import asyncio
import errno
import io
import json
import logging
import os
import queue
import random
import shlex
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, ExitStack, contextmanager
from pathlib import Path
from subprocess import CalledProcessError
from types import TracebackType
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Literal,
    NotRequired,
    Self,
    cast,
)
from uuid import uuid4

import docker
import docker.errors
import docker.types
import pydantic
import tenacity
import yaml

# import diskcache as dc
from alcatraz.clusters._container_proc import ContainerProc
from alcatraz.clusters._serialization import SerializableBaseModel
from alcatraz.clusters.interface import (
    AlcatrazAsyncioCancelledError,
    AlcatrazCodeExecutorTimeoutError,
    AlcatrazOutOfDiskSpaceError,
    AlcatrazTimeoutInterruptError,
    AlcatrazUnexpectedSystemError,
    ExecutionResult,
)
from docker import DockerClient
from docker.errors import APIError, NotFound
from docker.models.containers import Container, ExecResult
from docker.models.networks import Network
from filelock import Timeout as LockTimeout
from filelock import UnixFileLock
from jupyter_client.asynchronous.client import AsyncKernelClient
from jupyter_client.manager import AsyncKernelManager
from pydantic import BaseModel, ConfigDict, Extra, Field, field_validator
from typing_extensions import TypedDict, override

logger = logging.getLogger(__name__)

_MAX_UPLOAD_SIZE = 1024 * 1024 * 1024
_WAIT_FOR_TIMEOUT_INTERRUPT = 10

# Matches SSH command
# Do not use dynamic ports here (32_768-65_535) because they are not guaranteed to be open on Linux.
_FREE_PORTS: set[int] = set(range(*map(int, os.getenv("FREE_PORTS", "10000-32767").split("-"))))

VS_CODE_PORT = 8000


class VolumeConfig(TypedDict):
    bind_source: str
    bind_dest: str
    # Defaults to RO
    mode: NotRequired[Literal["ro", "rw"]]


VolumesConfig = dict[str, VolumeConfig]
"""
A dictionary of volume names to volume configurations.

Note: We don't actually use the volume name currently; however, we may end up
using it in the future.
"""


class ContainerNetConfig(TypedDict):
    # The gateway IP address for the container's network
    gateway: str
    # The IP address of the host
    vm_private_ip: str
    # Subnet of the docker network containing all Alcatraz containers, in the format
    # X.X.X.X/Y
    subnet: str


class CommandOutputResult(TypedDict):
    # None if command is still running
    exit_code: int | None
    result: str
    running: bool


class ClusterConfig(ABC, SerializableBaseModel):
    image: str = "quay.io/jupyter/base-notebook:python-3.11"
    side_images: list[str] = Field(default_factory=list)
    pull_from_registry: bool = True
    wait_for_health: bool = True
    jupyter_setup: list[str] = Field(
        default_factory=lambda: ["jupyter", "kernel", "--ip", "0.0.0.0"]
    )
    environment: dict[str, Any] = {}
    azure_files_config: dict[str, Any] | None = None
    azure_container_config: dict[str, Any] | None = None
    docker_compose_yaml: str | None = None
    tmux_enabled: bool = False

    # Pydantic config
    model_config = ConfigDict(
        extra="ignore",
        # model_copy does not revalidate unless you set this: https://github.com/pydantic/pydantic/discussions/8960
        revalidate_instances="always",
    )

    @classmethod
    @field_validator("image")
    def _validate_image(cls, image: str) -> str:
        assert image.count(":") == 1, "Image should be in the format 'repo:tag'"
        return image

    @classmethod
    @field_validator("side_images")
    def _validate_side_images(cls, side_images: list[str]) -> list[str]:
        assert len(side_images) < 60, "Too many side images"
        for image in side_images:
            assert image.count(":") == 1, "Image should be in the format 'repo:tag'"

        return side_images

    @abstractmethod
    def build(self) -> "BaseAlcatrazCluster":
        pass


class LocalConfig(ClusterConfig):
    # The URL for the docker host. May be a TCP url or unix socket.
    docker_host: str = "unix:///var/run/docker.sock"
    local_network: bool = False  # whether to use network_mode="host"
    volumes_config: VolumesConfig = Field(default_factory=dict)

    @override
    def build(self) -> "LocalCluster":
        return LocalCluster(
            image=self.image,
            side_images=self.side_images,
            docker_host=self.docker_host,
            pull_from_registry=self.pull_from_registry,
            health_check=self.wait_for_health,
            local_network=self.local_network,
            jupyter_setup=self.jupyter_setup,
            environment=self.environment,
            volumes_config=self.volumes_config,
            azure_files_config=self.azure_files_config,
            azure_container_config=self.azure_container_config,
            docker_compose_yaml=self.docker_compose_yaml,
            tmux_enabled=self.tmux_enabled,
        )


@contextmanager
def _allocate_port() -> Generator[int, None, None]:
    """
    Gives you a random unallocated port.
    
    This function now actually checks if the port is available by attempting to bind to it
    before returning it, avoiding "port is already allocated" errors.
    """
    global _FREE_PORTS
    max_attempts = 10  # Limit number of attempts to avoid infinite loops
    
    for _ in range(max_attempts):
        if not _FREE_PORTS:
            logger.warning("No free ports available in the predefined range!")
            # Fallback to letting the OS choose a port
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            to_allocate = s.getsockname()[1]
            s.close()
            logger.info("Allocated OS-chosen port %d", to_allocate)
            try:
                yield to_allocate
            finally:
                logger.info("Freeing OS-chosen port %d", to_allocate)
            return
            
        # Try to get a port from our predefined list
        to_allocate = random.choice(list(_FREE_PORTS))
        _FREE_PORTS.remove(to_allocate)
        
        # Actually check if the port is available by attempting to bind to it
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("", to_allocate))
            s.close()
            logger.info("Allocated verified port %d", to_allocate)
            try:
                yield to_allocate
            finally:
                logger.info("Freeing port %d", to_allocate)
                _FREE_PORTS.add(to_allocate)
            return
        except OSError:
            # Port is actually in use, don't add it back to _FREE_PORTS
            logger.warning("Port %d is already in use despite being in _FREE_PORTS", to_allocate)
            continue
        finally:
            try:
                s.close()
            except:
                pass
    
    # If we've exhausted our attempts, fall back to letting the OS choose
    logger.warning("Failed to allocate a port after %d attempts, letting OS choose", max_attempts)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    to_allocate = s.getsockname()[1]
    s.close()
    logger.info("Allocated OS-chosen port %d", to_allocate)
    try:
        yield to_allocate
    finally:
        logger.info("Freeing OS-chosen port %d", to_allocate)


class _IOPubParentHeader(pydantic.BaseModel):
    msg_id: str
    version: str


class _IOPubMessage(BaseModel):
    msg_type: str
    parent_header: _IOPubParentHeader

    class Config:
        extra = Extra.allow  # Allow other fields


async def _pull_messages(
    client: AsyncKernelClient,
    timeout: float,
    run_id: str,
    code_message_id: str,
    start_time: float,
) -> AsyncIterator[_IOPubMessage]:
    while True:
        logger.debug(
            {
                "run_id": run_id,
                "code_message_id": code_message_id,
                "details": "pulling iopub message",
            }
        )

        time_remaining = timeout - (time.time() - start_time)
        if time_remaining <= 0:
            raise AlcatrazCodeExecutorTimeoutError(timeout)

        try:
            raw_message = await client.get_iopub_msg(timeout=time_remaining)
        except queue.Empty as e:
            # Exception triggers iff `time_remaining` seconds have elapsed with no iopub message received
            raise AlcatrazCodeExecutorTimeoutError(timeout) from e

        try:
            message = pydantic.TypeAdapter(_IOPubMessage).validate_python(raw_message)
        except ValueError as e:
            # Unknown message type encountered; log and sk
            logger.warning(str(e))
            # Skip this message and continue to the next one
            continue

        logger.debug(
            {"run_id": run_id, "code_message_id": code_message_id, "message": message.model_dump()}
        )

        if message.parent_header.msg_id != code_message_id:
            logger.debug(
                {
                    "run_id": run_id,
                    "code_message_id": code_message_id,
                    "details": "wrong parent message id; ignoring",
                }
            )
            continue

        yield message

        if (
            message.msg_type == "status"
            and message.model_dump()["content"]["execution_state"] == "idle"
        ):
            logger.debug(
                {
                    "run_id": run_id,
                    "code_message_id": code_message_id,
                    "details": "got idle status; breaking",
                }
            )
            break
        elif message.msg_type == "error":
            break


# @dc.Cache().memoize(expire=3600)  # Only run once an hour
@tenacity.retry(
    wait=tenacity.wait_random_exponential(),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING, exc_info=True),
    stop=tenacity.stop_after_delay(300),
    reraise=True,
)
async def _acr_login(registry_name: str) -> None:
    login_cmd = ["az", "acr", "login", "--name", registry_name]

    process = await asyncio.create_subprocess_exec(
        *login_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except asyncio.TimeoutError as e:
        process.kill()
        raise subprocess.TimeoutExpired(cmd=login_cmd, timeout=30) from e

    # Get the return code
    return_code = await process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(
            returncode=return_code, cmd=login_cmd, output=stdout, stderr=stderr
        )


class Limits(TypedDict):
    """
    Centralized list of timeouts and limits for Alcatraz. Not all timeouts are currently in this class.
    """

    # Timeout for RPC calls to the Docker daemon
    # This is the max time any Docker call can take, which also implies a maximum upper limit for
    # send_shell_command and other Docker calls.
    docker_client_timeout_seconds: int
    # Maximum time image pull can take. Image pull will be auto-retried until this timer expires.
    image_pull_timeout_seconds: int
    # Maximum number of remote machines that can be initializing (pulling and starting docker images)
    # at once. This is helpful to prevent overloading the docker registry.
    initialization_concurrency: int


DEFAULT_LIMITS: Limits = {
    # We effectively don't limit the Docker client timeout. Set it to one day.
    "docker_client_timeout_seconds": 24 * 60 * 60,
    "image_pull_timeout_seconds": 5 * 60,
    "initialization_concurrency": 128,
}


class ContainerRegistryCredentials(TypedDict):
    registry: str
    username: str
    password: str


class BaseAlcatrazCluster(ABC):
    environment: dict[str, str] | None = None
    volumes_config: VolumesConfig | None = None

    def __init__(
        self,
        main_image: str,
        side_images: list[str],
        runtime: str | None = None,  # runtime for all images
        pull_from_registry: bool = True,
        health_check: bool = True,
        local_network: bool = False,
        jupyter_setup: list[str] | None = None,
        is_nvidia_gpu_env: bool = False,  # you better have nvidia gpus on your machine if you use this
        privileged: bool = False,
        shm_size: str | None = None,
        mem_limit: str | None = None,
        limits: Limits = DEFAULT_LIMITS,
        container_registry_credentials: ContainerRegistryCredentials | None = None,
        docker_compose_yaml: str | None = None,
        tmux_enabled: bool = False,
        docker_host: str = "unix:///var/run/docker.sock",
    ):
        if jupyter_setup is None:
            jupyter_setup = ["jupyter", "kernel", "--ip", "0.0.0.0"]
        self.docker_host = docker_host
        self.main_image = main_image
        self.side_images = side_images
        self.runtime = runtime
        self.pull_from_registry = pull_from_registry
        self.health_check = health_check
        self.local_network = local_network
        self.jupyter_setup = jupyter_setup
        self.pty_sockets: dict[str, Any] = {}
        self.backup_buffers: dict[str, io.BytesIO] = {}
        self.container_procs: dict[str, ContainerProc] = {}
        self.is_nvidia_gpu_env = is_nvidia_gpu_env
        self.privileged = privileged
        self.shm_size = shm_size
        self.mem_limit = mem_limit
        self.limits = limits
        self.container_registry_credentials = container_registry_credentials
        self.docker_compose_yaml = docker_compose_yaml
        self.tmux_enabled = tmux_enabled
        self.cmd_id_to_exec_id: dict[str, Any] = {}
        self._exit_stack = AsyncExitStack()

    @abstractmethod
    async def _get_docker_client(self) -> DockerClient:
        raise NotImplementedError()

    # @tenacity.retry(
    #     wait=tenacity.wait_fixed(1),
    #     retry=tenacity.retry_if_exception_type(APIError),
    #     before_sleep=tenacity.before_sleep_log(logger, logging.WARNING, exc_info=True),
    #     stop=tenacity.stop_after_delay(60),
    #     reraise=True,
    # )
    async def _create_container(
        self,
        container_ports: list[int] | None = None,
        force_host_ports: list[int] | None = None,
        **kwargs: Any,
    ) -> tuple[list[int], Container]:
        stack = ExitStack().__enter__()
        if container_ports is None:
            container_ports = []
        try:
            host_port_leases = force_host_ports or [
                stack.enter_context(_allocate_port()) for _ in range(len(container_ports))
            ]

            logger.info(
                "Allocated host ports %s -> container ports %s", host_port_leases, container_ports
            )

            ctr = cast(
                Container,
                await asyncio.to_thread(
                    self.docker_client.containers.run,  # type: ignore
                    **kwargs,
                    ports={
                        f"{ctr_port}/tcp": host_port  # container port on left. host port on right
                        for ctr_port, host_port in zip(container_ports, host_port_leases)
                    },
                ),
            )
            if isinstance(self, LocalCluster):
                # Add the container to the exit stack so it gets removed when we're done.
                self._exit_stack.push_async_callback(
                    lambda: asyncio.to_thread(ctr.remove, force=True)
                )
            # Also free our host port leases when we're done with this container.
            self._exit_stack.push(stack.__exit__)
            logger.info("Started new container! Container name: %s", ctr.name)

            return host_port_leases, ctr
        except Exception:
            # Free the ports if we fail to start the container.
            stack.__exit__(*sys.exc_info())
            raise

    async def _pull_image(self, i: str) -> None:
        # Ideally, we would only retry if not docker.errors.NotFound, to crash quickly when the image is misspelled.
        # However, since this code is also used by all workers in the cluster, we can overload ACR. This often
        # manifests in authentication failing, and subsequently throwing docker.errors.NotFound. So we retry on everything.
        @tenacity.retry(
            wait=tenacity.wait_random_exponential(max=60),
            before_sleep=tenacity.before_sleep_log(logger, logging.WARNING, exc_info=True),
            stop=tenacity.stop_after_delay(self.limits["image_pull_timeout_seconds"]),
            reraise=True,
        )
        async def _pull_image_inner() -> None:
            await asyncio.to_thread(self.docker_client.images.pull, i)

        await _pull_image_inner()

    async def _start(self) -> None:
        # Exit stack handles removing all the containers and networks when we're done.
        self.socat_container: Container | None = None
        self._kernel: AsyncKernelClient | None = None
        self._code_server_socat_container: Container | None = None
        self._code_server: ExecResult | None = None
        self.container_group_name = f"alcatraz-{uuid4()}"

        docker_client_initialized = False

        images = [self.main_image] + self.side_images
        if self.container_registry_credentials:
            # Generic docker login
            self.docker_client = await self._get_docker_client()
            docker_client_initialized = True
            self.docker_client.login(
                username=self.container_registry_credentials["username"],
                password=self.container_registry_credentials["password"],
                registry=self.container_registry_credentials["registry"],
            )
        else:
            # Azure Container Registry login
            acr_registries = {
                image.split(".azurecr.io")[0] for image in images if ".azurecr.io" in image
            }
            for registry_name in acr_registries:
                await _acr_login(registry_name)

        if not docker_client_initialized:
            self.docker_client = await self._get_docker_client()

        self._exit_stack.push_async_callback(lambda: asyncio.to_thread(self.docker_client.close))
        logger.info("Docker info: %s", self.docker_client.info()["KernelVersion"])

        for image in images:
            if self.pull_from_registry:
                logger.info("Pulling %s", image)
                # TODO footgun warning: if user provides an image that has full acr prefix but we see they have a local image of the same name (without the prefix) and without a tag to associate it with the remote image, warn the user or maybe just skip pulling...
                # if fails, error message is that image doesn't exist or may require docker login. Rewrite to say image doesn't exist or may require az acr login --name <acr_name> --subscription <subscription_id_or_name>
                await self._pull_image(image)
                logger.info("Pulled %s", image)
            else:
                logger.info("Skipping pull for %s", image)

        logger.info("Creating network for %s", self.main_image)
        try:
            self.docker_network = await asyncio.to_thread(
                self.docker_client.networks.create, "tinydockernet-" + self.container_group_name
            )
        except docker.errors.APIError as e:
            if "all predefined address pools have been fully subnetted" in str(e):
                raise RuntimeError(
                    "Too many docker networks have been created. Most machines/laptops default to allowing 16 LocalCluster instances."
                ) from e
            raise
        if isinstance(self, LocalCluster):
            self._exit_stack.push_async_callback(
                lambda: asyncio.to_thread(self.docker_network.remove)
            )

        self.containers: list[Container] = []

        # Start the main container
        logger.info("Starting main container for %s", self.main_image)

        volume_config = {}
        if self.volumes_config:
            for volume_cfg in self.volumes_config.values():
                logger.info(
                    f"Mounting volume from {volume_cfg['bind_source']} to destination {volume_cfg['bind_dest']}"
                )
                # In Docker, name of volume = source, and "bind" = target in the container
                volume_config.update(
                    {
                        volume_cfg["bind_source"]: {
                            "bind": volume_cfg["bind_dest"],
                            "mode": volume_cfg.get("mode", "ro"),
                        }
                    }
                )

        environment = {
            "GRANT_SUDO": "yes",
            "CHOWN_HOME": "yes",
            "NB_USER": "jovyan",
            "NB_UID": "1000",
            "NB_GID": "100",
        }
        environment.update(self.environment) if self.environment else None

        if self.runtime:
            runtime = self.runtime
        else:
            runtime = "nvidia" if self.is_nvidia_gpu_env else "runc"

        if runtime == "sysbox-runc":
            _setup_cmds: list[str | None] = [
                "wget https://downloads.nestybox.com/sysbox/releases/v0.6.4/sysbox-ce_0.6.4-0.linux_amd64.deb -O /tmp/sysbox-ce_0.6.4-0.linux_amd64.deb",
                "sudo systemctl stop unattended-upgrades" if self.tmux_enabled else None,
                "docker rm $(docker ps -a -q) -f",
                "sudo apt-get update",
                "sudo apt-get install -y jq linux-headers-$(uname -r)",
                "sudo apt-get install -y /tmp/sysbox-ce_0.6.4-0.linux_amd64.deb",
                "sudo systemctl status sysbox -n20",
            ]
            setup_cmds: list[str] = [str(cmd) for cmd in _setup_cmds if cmd is not None]
            for cmd in setup_cmds:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                # check for non-zero exit code
                if result.returncode != 0:
                    raise AlcatrazUnexpectedSystemError(
                        f"Failed to install sysbox runtime"
                        f" Command {cmd} failed with exit code {result.returncode}."
                        f" stdout: {result.stdout}, stderr: {result.stderr}"
                    )
                logger.info(result.stdout)

        for i, image in enumerate(images):
            _, ctr = await self._create_container(
                image=image,
                name=f"container{i}-{self.container_group_name.split('alcatraz-')[1]}",
                runtime=runtime if i == 0 else "runc",
                device_requests=(
                    [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]
                    if self.is_nvidia_gpu_env and i == 0
                    else []
                ),
                stdin_open=True,
                tty=True,
                detach=True,  # Equivalent to '-d'
                remove=False,
                network_mode=(
                    "host" if self.local_network else "tinydockernet-" + self.container_group_name
                ),
                user=0,
                environment=environment,
                volumes=(i == 0 and volume_config) or {},
                privileged=self.privileged and i == 0,
                shm_size=self.shm_size if i == 0 else None,
                mem_limit=self.mem_limit if i == 0 else None,
            )
            self.containers.append(ctr)

        if self.docker_compose_yaml:
            logger.info("Using docker-compose file")
            await self._start_docker_compose()

        if self.tmux_enabled:
            await self._setup_tmux()

    async def _setup_tmux(self) -> None:
        self.wait_for_health(str(self.containers[0].name))
        exit_code, _ = self.containers[0].exec_run(cmd="tmux -V")
        if exit_code:
            logger.info("tmux not found. Installing tmux....")
            self.containers[0].exec_run(cmd=["apt-get", "update"])
            exit_code = (
                self.containers[0].exec_run(cmd=["apt-get", "install", "-y", "tmux"]).exit_code
            )
            if exit_code != 0:
                raise AlcatrazUnexpectedSystemError(
                    "Failed to install tmux in main container"
                    f" Failed with exit code {exit_code}."
                )

    async def _stop(self) -> None:
        # Close kernel -> jupyter connections and destroy the zmq context to prevent
        # sockets from being leaked
        logger.info("Shutting down %s", self.container_group_name)
        # Release exit stack resources
        await self._exit_stack.aclose()

    async def __aenter__(self) -> Self:
        try:
            await self._start()
        except Exception:
            # if an exception is thrown in __aenter__, __aexit__ won't run
            await self.__aexit__(*sys.exc_info())
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, exc_tb
        await self._stop()

    def wait_for_health(self, container_id: str) -> bool:
        """Wait for a Docker container to be healthy.

        Args:
            container_id (str): ID of the container.

        Returns:
            bool: True if the container is healthy, False if not or if 60s timeout occurred
        """
        start_time = time.monotonic()

        while time.monotonic() - start_time < 60:
            container = self.docker_client.containers.get(container_id)
            attrs = cast(Any, container.attrs)
            if "Health" not in attrs["State"]:
                logger.warning("Container health not available for this container, ignoring.")
                return True
            status = attrs["State"]["Health"]["Status"]
            if status == "healthy":
                return True
            elif status == "unhealthy":
                print("Container became unhealthy.")
                return False
            time.sleep(0.2)  # Check every 10 seconds

        print("Timeout reached without becoming healthy.")
        return False

    async def fetch_container_names(self) -> list[str]:
        try:
            return [str(c.name) for c in self.containers]
        except AttributeError:  # self.containers not set since __aenter__ hasn't happened yet.
            return []

    async def send_shell_command(
        self,
        cmd: str,
        timeout: int | None = None,
        user: str | None = None,
        container_id: int = 0,
        environment: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> ExecutionResult:
        assert (
            timeout is None or timeout < self.limits["docker_client_timeout_seconds"]
        ), f"{timeout=} must be less than {self.limits['docker_client_timeout_seconds']=} (which you can configure)"
        """
        Not recommended. But for quick testing. It uses docker exec under the hood so directory changes aren't preserved.

        Args:
            cmd (str): Command to run
            timeout (int, optional): Timeout in seconds. Defaults to 60.
            user (str, optional): User to run the command as. Defaults to "" (root).
        Returns:
            dict[str, Any]: {"exit_code": int, "result": bytes}
        """

        if type(cmd) is not str:
            raise ValueError(f"cmd must be of type string, but it was type {type(cmd)}")
        exit_code, result = await asyncio.to_thread(
            self.containers[container_id].exec_run,
            cmd=(
                ["sh", "-c", cmd]
                if timeout is None
                else ["timeout", f"{timeout}s", "sh", "-c", cmd]
            ),
            user=user or "",
            environment=environment,
            workdir=workdir,
        )

        # the terminal may output invalid UTF-8
        logger.debug(
            "cmd %s -> (%d) %s", cmd, exit_code, result.decode("utf-8", errors="backslashreplace")
        )
        return {"exit_code": exit_code, "result": result}

    async def fetch_container_logs(self, container_id: int = 0, tail: int = 1000) -> bytes:
        return await asyncio.to_thread(self.containers[container_id].logs, tail=tail)

    async def send_shell_command_is_done(self, cmd_id: str) -> bool:
        if self.tmux_enabled:
            output = await self.send_shell_command(f"cat /tmp/{cmd_id}_exit_code")
            if "no space left on device" in output["result"].decode("utf-8"):
                raise AlcatrazOutOfDiskSpaceError(
                    f"No space left on device! Triggered when running:\n{cmd_id}"
                )

            assert output["exit_code"] == 0, f"Failed to get exit code for cmd_id {cmd_id}"
            return output["result"].decode("utf-8").strip() != ""
        else:
            exec_inspect = self.docker_client.api.exec_inspect(self.cmd_id_to_exec_id[cmd_id])
            return not exec_inspect["Running"]

    async def send_shell_command_get_result(
        self, cmd_id: str, allow_unfinished: bool = False, content_idx: int = 0
    ) -> CommandOutputResult:
        """
        Get the result of a running shell command started with `send_shell_command_and_get_cmd_id`.

        Args:
            cmd_id (str): Command ID returned from `send_shell_command_and_get_cmd_id`.
            allow_unfinished (bool, optional): If False, raises an AssertionError if the command is still running.
            content_idx (int, optional):
                Start displaying the output from this **line**. Defaults to 0. Note that the
                output always includes a header line with the line number.
        """

        done = await self.send_shell_command_is_done(cmd_id)
        if not allow_unfinished:
            assert done, f"Command with cmd_id {cmd_id} hasn't finished running!"

        # If done, the exit code is stored in /tmp/{cmd_id}_exit_code. Let's download the file.
        exit_code_output = await self._check_shell_command(f"cat /tmp/{cmd_id}_exit_code")
        try:
            exit_code = int(exit_code_output.strip())
        except Exception:
            exit_code = None

        result = (
            self.containers[0]
            .exec_run(cmd=["sh", "-c", f"cat /tmp/{cmd_id}_out"])
            .output.decode("utf-8", errors="replace")
            .strip()
        )

        # Display the lines from idx onwards
        result_tail = "\n".join(result.split("\n")[content_idx:])
        result = f"From line #{content_idx}...\n{result_tail}"

        return {"exit_code": exit_code, "result": result, "running": not done}

    def clean_send_shell_command_state(self, cmd_id: str) -> None:
        assert cmd_id in self.cmd_id_to_exec_id, f"Command state with cmd_id {cmd_id} not present!"
        del self.cmd_id_to_exec_id[cmd_id]

    async def pause_container(self) -> None:
        self.containers[0].pause()

    async def unpause_container(self) -> None:
        self.containers[0].unpause()

    async def create_pty_socket(self, socket_id: str, user: str | None = None) -> bool:
        exec_instance = self.containers[0].exec_run(
            cmd="/bin/bash", tty=True, stdin=True, socket=True, user=user or ""
        )
        self.pty_sockets[socket_id] = exec_instance.output
        self.backup_buffers[socket_id] = io.BytesIO()
        self.pty_sockets[socket_id]._sock.setblocking(0)
        return True

    async def send_pty_input(self, socket_id: str, input_bytes: bytes) -> None:
        socket = self.pty_sockets[socket_id]
        socket._sock.send(input_bytes)

    async def read_pty_output(self, socket_id: str, is_retry: bool = False) -> bytes:
        s = self.pty_sockets[socket_id]
        backup_buffer = self.backup_buffers[socket_id]

        # If we are not retrying, we need to clear the buffer
        if not is_retry:
            backup_buffer.seek(0)
            backup_buffer.truncate(0)

        while True:
            try:
                backup_buffer.write(s._sock.recv(4096))
            except socket.error as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    return backup_buffer.getvalue()
                logger.exception("pty read failed", exc_info=e)
                raise

    async def spawn_proc(self, cmd: list[str], stdin: bool = True) -> str:
        """Spawns a process in the container using the specified command and
        returns a handle that can be used with the other proc_* methods.

        In practice, after spawning a process, the caller is expected to poll
        for output using proc_read_output() until the process is complete.

        Note that if the caller specifies stdin=True, the caller is responsible
        for closing stdin via proc_close_stdin() when they are done.
        """
        exec_id = self.docker_client.api.exec_create(
            self.containers[0].id,
            cmd=cmd,
            stdin=stdin,
            stdout=True,
            stderr=True,
            tty=False,
        )
        sock = self.docker_client.api.exec_start(exec_id, tty=False, socket=True)
        assert hasattr(sock, "_sock")
        private_sock_impl: socket.socket = sock._sock
        container_proc = ContainerProc(private_sock_impl, self.docker_client.api, exec_id)
        handle = str(uuid.uuid4())
        self.container_procs[handle] = container_proc
        return handle

    async def proc_write_stdin(self, handle: str, data: bytes) -> None:
        return self.container_procs[handle].write_stdin(data)

    async def proc_close_stdin(self, handle: str) -> None:
        return self.container_procs[handle].close_stdin()

    async def proc_read_output(self, handle: str) -> tuple[int | None, bytes]:
        return self.container_procs[handle].read_output()

    async def proc_is_running(self, handle: str) -> bool:
        return self.container_procs[handle].is_running()

    async def _shell_exit_code(self, cmd: str) -> int:
        logger.debug("running %s", cmd)
        return (await self.send_shell_command(cmd))["exit_code"]

    async def _check_shell_command(self, cmd: str) -> str:
        logger.debug("Running %s", cmd)
        res = await self.send_shell_command(cmd)
        if res["exit_code"] != 0:
            raise CalledProcessError(res["exit_code"], cmd, res["result"])
        return res["result"].decode("utf-8")

    async def _jupyter_runtime_dir(self) -> str:
        return (await self._check_shell_command("jupyter --runtime-dir")).strip()

    async def _jupyter_list_connection_files(self) -> list[dict[str, Any]]:
        runtime_dir = await self._jupyter_runtime_dir()
        try:
            connection_file_path = (
                await self._check_shell_command(f"ls {runtime_dir}/kernel-*.json")
            ).strip()
        except CalledProcessError:
            # ls will return -1 if no files are found
            return []

        # split
        connection_files = connection_file_path.split("\n")
        files = [
            await self.download(connection_file_path) for connection_file_path in connection_files
        ]
        return [json.loads(file) for file in files if file]

    async def _jupyter_start_kernel(self) -> None:
        res = await asyncio.to_thread(
            self.containers[0].exec_run,
            cmd=self.jupyter_setup,
            stream=True,
            demux=False,
        )
        try:
            n = await asyncio.to_thread(next, res.output)
            logger.info("Jupyter output:\n%s", n.decode("utf-8", errors="ignore"))
        except StopIteration:
            logger.info("Jupyter process exited")
            return

    async def _jupyter_wait_for_connection_file(self) -> dict[str, Any]:
        """
        Fetches Jupyter connection file
        """
        # Wait for health check to start up
        if self.health_check:
            self.wait_for_health(str(self.containers[0].id))
        else:
            await asyncio.sleep(2)

        assert len(await self._jupyter_list_connection_files()) == 0, (
            "A jupyter kernel is already running before we started one. "
            "Does your container image start Jupyter by default? This is not "
            "supported, and you should change your image to not start Jupyter "
            "by default."
        )

        self._exit_stack.callback(asyncio.create_task(self._jupyter_start_kernel()).cancel)

        async with asyncio.timeout(60):
            # Poll in runtime_dir until we find the connection file path.
            while True:
                connection_files = await self._jupyter_list_connection_files()
                assert len(connection_files) <= 1
                if connection_files:
                    connection_file = connection_files[0]
                    break
                await asyncio.sleep(0.1)

        logger.info("Connection file: %s", connection_file)

        return connection_file

    async def _ensure_jupyter_installed(self, force_python_install: bool) -> None:
        python_not_installed = await self._shell_exit_code("python --version")
        pip_not_installed = await self._shell_exit_code("pip --version")
        if python_not_installed or pip_not_installed:
            if not force_python_install:
                raise ValueError(
                    "The provided image does not have python installed. Alcatraz can install python for you but you must use the force_python_install flag on this method."
                )
            logger.info("Python: %d, Pip: %d", python_not_installed, pip_not_installed)
            await self._check_shell_command(
                "apt-get update && apt-get install -y python3 python3-pip"
            )
        jupyter_not_installed = await self._shell_exit_code("jupyter --version")
        if jupyter_not_installed:
            await self._check_shell_command("pip install jupyter")

    async def get_container_net_config(self) -> ContainerNetConfig:
        assert (
            not self.local_network
        ), "Net config cannot be fetched when running as network_mode=host"
        # All Alcatraz containers are on the same network if self.local_network is disabled

        self.docker_network.reload()
        settings = self.docker_network.attrs["IPAM"]["Config"][0]

        gateway = None
        subnet = None
        if settings.get("Gateway", None):
            gateway = settings["Gateway"]
        if settings.get("Subnet", None):
            subnet = settings["Subnet"]
        assert gateway, "Gateway not found"
        assert subnet, "Subnet mask not found"

        # Read the non-localhost IP address of the current host
        # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 1))  # connect() for UDP doesn't send packets
        vm_private_ip = s.getsockname()[0]

        return {
            "subnet": subnet,
            "gateway": gateway,
            "vm_private_ip": vm_private_ip,
        }

    async def add_weak_network_block_via_ip_tables(self) -> None:
        """
        Blocking internet access with IP tables isn't super secure tbh. Model can escape container to change the VM level IP table.
        This is fine for some use cases. Bad for others. Think carefully and/or reach out in #alcatraz

        We block external access using a two part strategy:

        1. Block ctr network -> internet using DOCKER-USER, which is attached to the FORWARD chain (= packets whose src/dest isn't the host VM).
           This prevents ctr -> internet, but *not* ctr -> host since that's handled by the INPUT chain.
        2. Block ctr network -> host using INPUT. We still allow established host -> ctr connections (although I don't think this is used for anything)

        Note: we still allow

        1. ctr2 -> ctr connections, which is required for Jupyter kernel communication.
        2. ctr -> ctr2 connections, which is required for CTF challenges.

        We then sanity check by opening a url and ensuring it doesn't work.
        """

        net_config = await self.get_container_net_config()
        subnet = net_config["subnet"]

        # Don't forget to update `undo_weak_network_block_via_ip_tables` if you change this!
        cmd_template = """
        # Container network ----------
        # Allow already established connections into the container
        iptables -I DOCKER-USER 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
        # Allow container to communicate within the Docker network (ctr -> ctr2)
        iptables -I DOCKER-USER 2 -s {subnet} -d {subnet} -j ACCEPT
        # Reject all other outgoing connections from the container to the world
        iptables -I DOCKER-USER 3 -s {subnet} -j REJECT

        # Host communications --------
        # Allow preexisting connections (so ctr -> host comms are allowed if the host initiated them)
        # This is necessary for jupyter ports which are published to the host and the host will initiate the connection
        iptables -I INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
        # Prevent container from accessing host. (INPUT = host input)
        iptables -I INPUT 2 -s {subnet} -j REJECT
        """

        # run as a tempfile
        with tempfile.NamedTemporaryFile(mode="w") as f:
            f.write(cmd_template.format(subnet=shlex.quote(subnet)))
            f.flush()

            await async_subprocess_run(["bash", f.name])

        try:
            await self._check_shell_command(
                "python -c \"import urllib.request; urllib.request.urlopen('http://example.com', timeout=5)\""
            )
        except Exception:
            pass
        else:
            assert False, "Setting up network block with IP tables failed"

    async def undo_weak_network_block_via_ip_tables(self) -> None:
        """
        Removes the iptables rules set up by add_weak_network_block_via_ip_tables.
        """
        await async_subprocess_run(["sudo", "iptables", "-D", "INPUT", "2"])
        await async_subprocess_run(["sudo", "iptables", "-D", "INPUT", "1"])
        # Undoing in reverse is important!!
        await async_subprocess_run(["sudo", "iptables", "-D", "DOCKER-USER", "3"])
        await async_subprocess_run(["sudo", "iptables", "-D", "DOCKER-USER", "2"])
        await async_subprocess_run(["sudo", "iptables", "-D", "DOCKER-USER", "1"])

        check_result = await self.send_shell_command(
            "python -c \"import urllib.request; urllib.request.urlopen('http://example.com', timeout=5)\""
        )
        # NOTE: python is not present in all images
        assert check_result["exit_code"] in (0, 127), "Failed to undo network block"

    async def is_kernel_started(self) -> bool:
        return self._kernel is not None

    async def create_kernel_on_machine(
        self, language: str = "python3", force_python_install: bool = False
    ) -> None:
        del language  # TODO implement language support
        if self._kernel:
            raise ValueError("Kernel already created.")

        await self._ensure_jupyter_installed(force_python_install)

        # expose kernel ports on host machine
        connection_file = await self._jupyter_wait_for_connection_file()
        ports_to_forward = [v for k, v in connection_file.items() if k.endswith("_port")]
        logger.info("Jupyter kernel ports: %s", ports_to_forward)

        logger.info("starting socat containers for jupyter!")
        assert not self.socat_container, "socat container already exists!"
        host_port_leases, self.socat_container = await self._create_container(
            container_ports=ports_to_forward,
            force_host_ports=None if isinstance(self, LocalCluster) else list(range(11000, 11005)),
            image="alpine/socat",
            tty=True,
            name="alpinesocat-jupyter-" + self.container_group_name,
            detach=True,  # Equivalent to '-d'
            remove=True,  # Equivalent to '--rm'
            network_mode="tinydockernet-" + self.container_group_name,  # Equivalent to '--network'
            entrypoint="/bin/sh",
            # override socat entrypoint with a placeholder. We'll call socat ourselves and many times not just once!
        )
        logger.info("forwarding ports %s", ports_to_forward)
        await asyncio.gather(
            *(
                asyncio.to_thread(
                    self.socat_container.exec_run,
                    cmd=[
                        "socat",
                        f"TCP4-LISTEN:{p},fork",
                        f"TCP4:{self.containers[0].name}:{p}",
                    ],
                    detach=True,
                )
                for p in ports_to_forward
            )
        )

        # Replace the ports in the connection file with the host ports
        for k, v in connection_file.items():
            if k.endswith("_port"):
                logger.debug(
                    "replacing %s with %s",
                    v,
                    next(
                        h
                        for h, ctr_port in zip(host_port_leases, ports_to_forward)
                        if v == ctr_port
                    ),
                )
                connection_file[k] = next(
                    h for h, ctr_port in zip(host_port_leases, ports_to_forward) if v == ctr_port
                )

        logger.info("connecting to kernel!")
        # connect to the kernel
        self._km = AsyncKernelManager(owns_kernel=False)
        logger.info("edited connection file %s", connection_file)
        self._km.load_connection_info(connection_file)
        self._kernel = self._km.client()
        logger.info("starting channels")
        self._kernel.start_channels()
        logger.info("connected")

        async def cleanup() -> None:
            assert self._kernel
            self._kernel.stop_channels()
            zmq_context = self._kernel.context
            zmq_context.destroy()
            await self._km.cleanup_resources()

        self._exit_stack.push_async_callback(cleanup)

        await self._kernel.wait_for_ready(timeout=60.0)
        assert await self.kernel_is_alive()
        logger.info("Kernel is alive!")

    async def kernel_is_alive(self) -> bool:
        is_alive = cast(bool, self._kernel and await self._kernel.is_alive())
        assert isinstance(is_alive, bool)

        return is_alive

    async def _interrupt_kernel(self) -> None:
        """
        The KM interrupt code doesn't work because it assumes that the KernelManager owns the kernel.
        However, interrupting a kernel is very simple: send it a SIGINT. We can do this using Docker!
        """
        assert self._kernel
        # kernel creates the python -m ipykernel_launcher process; it interrupts when receiving
        # sigint. kill it with sigint
        exit_code, output = await asyncio.to_thread(
            self.containers[0].exec_run, cmd=["pkill", "-INT", "-f", "ipykernel_launcher"]
        )
        assert exit_code == 0, f"Failed to interrupt kernel: {output}"

    async def send_kernel_command(self, command: str, timeout: int = 20) -> list[dict[str, Any]]:
        if not self._kernel:
            raise ValueError("kernel not created yet.")
        if timeout <= 0:
            raise ValueError(f"timeout must be positive, got {timeout=}")

        code_message_id = self._kernel.execute(
            command,
            silent=False,
            store_history=True,
            allow_stdin=False,
        )
        run_id = str(uuid.uuid4())
        output: list[dict[str, Any]] = []
        try:
            try:
                # TODO handle comm_open messages
                async for message in _pull_messages(
                    self._kernel, timeout, run_id, code_message_id, time.time()
                ):
                    output.append(message.model_dump())
                    if message.msg_type == "error":
                        return output

                logger.debug(
                    {
                        "run_id": run_id,
                        "code_message_id": code_message_id,
                        "details": "execution completed successfully",
                    }
                )
            except AlcatrazCodeExecutorTimeoutError:
                await self._interrupt_kernel()
                output.append({"msg_type": "@timeout", "timeout": timeout})

                # After sending an interrupt, wait a bit longer to capture the keyboard interrupt traceback. This maybe be
                # useful for debugging to, for example, see where the code was stuck.
                try:
                    async for message in _pull_messages(
                        self._kernel,
                        _WAIT_FOR_TIMEOUT_INTERRUPT,
                        run_id,
                        code_message_id,
                        start_time=time.time(),  # wait some additional time for the interrupt to be handled
                    ):
                        output.append(message.model_dump())
                        if message.msg_type == "error":
                            return output

                    # even though we sent an interrupt, we actually finished successfully
                    logger.info(
                        {
                            "run_id": run_id,
                            "code_message_id": code_message_id,
                            "details": "execution completed successfully without exception from timeout",
                        }
                    )
                except AlcatrazCodeExecutorTimeoutError as e:
                    raise AlcatrazTimeoutInterruptError(
                        "Did not hear back after timeout interrupt was sent."
                    ) from e
        except asyncio.CancelledError as cancelled_error:
            logger.info({"run_id": run_id, "details": "execution cancelled by the user/client"})
            await self._interrupt_kernel()
            await asyncio.sleep(0.5)
            raise AlcatrazAsyncioCancelledError(
                "Execution cancelled by the user/client"
            ) from cancelled_error
        except Exception as e:
            logger.exception(
                {
                    "run_id": run_id,
                    "details": "execution failed with exception in plumbing",
                    "error": e,
                }
            )
            await self._interrupt_kernel()
            await asyncio.sleep(0.5)
            raise AlcatrazUnexpectedSystemError(
                "Execution failed with exception in plumbing"
            ) from e
        return output

    async def delete_kernel_on_machine(self) -> None:
        """What do you need this for??"""
        if self._kernel:
            self._kernel.shutdown()

    async def download_tar(self, source: str, container_id: int = 0) -> bytes:
        assert os.path.isabs(source), "Source must be an absolute path"

        tar_generator, _stat = self.containers[container_id].get_archive(source)

        # Convert Generator[bytes] -> IO[bytes]
        bytes_io = io.BytesIO()
        for chunk in tar_generator:
            bytes_io.write(chunk)
        bytes_io.seek(0)
        return bytes_io.getvalue()

    async def download(self, source: str, container_id: int = 0) -> bytes:
        b = await self.download_tar(source, container_id=container_id)
        with tarfile.open(fileobj=io.BytesIO(b), mode="r") as tar:
            tar_info = tar.next()
            assert tar_info, f"File {source} not found in container"
            assert (f := tar.extractfile(tar_info))
            return f.read()

    async def upload(
        self, file: bytes, destination: str, container_id: int = 0, chown: bool = True
    ) -> None:
        if not os.path.isabs(destination):
            raise ValueError("Destination must be an absolute path")

        container = self.containers[container_id]
        try:
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar_info = tarfile.TarInfo(name=os.path.basename(destination))
                tar_info.size = len(file)
                if tar_info.size > _MAX_UPLOAD_SIZE:
                    raise ValueError(
                        f"File too large. Max is {_MAX_UPLOAD_SIZE:,} bytes",
                    )
                tar.addfile(tar_info, fileobj=io.BytesIO(file))

            await asyncio.to_thread(
                container.put_archive, os.path.dirname(destination), tar_stream.getvalue()
            )

            # print(success) # TODO when does this fail w/o throwing an exception??

            # Warning: if there is a process on the server that immediately deletes the file, chown will fail due to the race condition.
            # This was needed for the API proxy. For now, we resolve this by optionally not chowning the file (chown=False)
            if chown:
                container_user = (
                    (await asyncio.to_thread(container.exec_run, cmd=["whoami"]))
                    .output.decode()
                    .strip()
                )
                container_group = (
                    (await asyncio.to_thread(container.exec_run, cmd=["id", "-g"]))
                    .output.decode()
                    .strip()
                )
                exit_code, _output = await asyncio.to_thread(
                    container.exec_run,
                    cmd=["chown", container_user + ":" + container_group, destination],
                    user="root",
                )
                assert exit_code == 0, f"Failed to chown {destination}: {_output.decode('utf-8')}"
        except APIError as api_error:
            try:
                return_code, _ = await asyncio.to_thread(
                    container.exec_run, cmd=["rm", destination]
                )
                assert return_code == 0
            except Exception as e:
                print(f"Error while removing file: {destination}", e)
            # TODO clean exception for path not existing vs other problems
            if isinstance(api_error, NotFound):
                raise ValueError(f"Destination path does not exist {destination}") from api_error
            else:
                raise

    @abstractmethod
    def serialize(self) -> ClusterConfig:
        pass

    async def commit_and_push(
        self,
        repository: str,
        tag: str,
        credentials: ContainerRegistryCredentials | None,
        container_id: int = 0,
        acr_login: bool = True,
    ) -> bool:
        logger.info(f"commit_and_push {repository}:{tag}")
        assert credentials or acr_login, "must provide credentials or allow acr_login"
        assert not (
            credentials and acr_login
        ), "cannot use both credentials and allow acr_login (disable acr_login if passing credentials)"
        container = self.containers[container_id]
        container.commit(repository=repository, tag=tag)
        if credentials:
            self.docker_client.login(
                username=credentials["username"],
                password=credentials["password"],
                registry=credentials["registry"],
            )
            docker_client_push = self.docker_client
        elif acr_login:
            assert "azurecr.io" in repository
            registry_name = repository.split(".azurecr.io")[0]
            await _acr_login(registry_name)
            docker_client_push = docker.from_env(
                environment={"DOCKER_HOST": self.docker_host},
                max_pool_size=1000,
                timeout=self.limits["docker_client_timeout_seconds"],
            )
        res = docker_client_push.images.push(repository=repository, tag=tag)
        logger.info(f"pushed {repository}:{tag}")
        final_res = json.loads(res.strip().split("\n")[-1])
        if "error" in final_res:
            raise RuntimeError(f"Error pushing image: {final_res['error']}")

        return True

    async def _start_docker_compose(self) -> None:
        assert (
            self.docker_compose_yaml
        ), "you should only call this if you've set docker_compose_yaml"

        main_network = "tinydockernet-" + self.container_group_name
        docker_compose_dict = yaml.safe_load(self.docker_compose_yaml)

        # We don't let docker-compose files expose ports to the host, since this can mess up the host.
        # Containers should only be accessible through the network we create for them.
        for service_name, service_value in docker_compose_dict.get("services", {}).items():
            if service_value.get("ports"):
                raise RuntimeError(
                    f"Service {service_name} has ports exposed to the host. You should remove this. Containers can still talk through the network."
                )

        external_networks = [
            network_name
            for network_name, network_value in docker_compose_dict.get("networks", {}).items()
            if network_value.get("external")
        ]
        if len(external_networks) > 1:
            raise RuntimeError(
                f"At most one external network is allowed; found {len(external_networks)}"
            )
        # If there is one external network, we'll set the name to the name of the network we already created.
        # Then we'll update the docker_compose_yaml string
        elif len(external_networks) == 1:
            external_network_name = external_networks[0]
            docker_compose_dict["networks"][external_network_name]["name"] = main_network
            logger.info("Using external network")
        docker_compose_str = yaml.dump(docker_compose_dict)

        # Write docker_compose_yaml to a temporary file
        with tempfile.NamedTemporaryFile("w") as f:
            f.write(docker_compose_str)
            f.flush()
            compose_file = f.name

            prior_networks = self.docker_client.networks.list()
            project_name = self.container_group_name.split("alcatraz-")[1]

            docker_compose_command = [
                "docker-compose",
                "--project-name",
                project_name,
                "--file",
                compose_file,
                "up",
                "--detach",
            ]
            await async_subprocess_run(docker_compose_command)

        docker_compose_containers = self.docker_client.containers.list(
            filters={"label": f"com.docker.compose.project={project_name}"}
        )
        self.containers.extend(docker_compose_containers)

        final_networks = self.docker_client.networks.list()
        new_networks = [network for network in final_networks if network not in prior_networks]

        for network in new_networks:
            if isinstance(self, LocalCluster):
                self._exit_stack.push_async_callback(
                    lambda network=network: asyncio.to_thread(network.remove)  # type: ignore
                )

        for ctr in docker_compose_containers:
            if isinstance(self, LocalCluster):
                self._exit_stack.push_async_callback(
                    lambda ctr=ctr: asyncio.to_thread(ctr.remove, force=True)  # type: ignore
                )
                self._exit_stack.push_async_callback(
                    lambda ctr=ctr: asyncio.to_thread(ctr.stop)  # type: ignore
                )

        # If docker-compose has an external network, we've already connected to it and are done.
        # If it doesn't, let's connect all the containers to the network we created for the main container.
        if not external_networks:
            logger.info("Connecting all networks to main_network")
            # Connect all networks to main_network
            for container in docker_compose_containers:
                self.docker_network.connect(container, aliases=[container.name])

    async def send_shell_command_and_get_cmd_id(
        self, cmd: str, timeout: int = 60, user: str | None = None
    ) -> str:
        """
        send_shell_command but detached. Status and result of command can be retrieved
        using returned cmd_id
        """
        del timeout  # TODO implement timeout
        user = user or ""
        cmd_id = str(uuid4())

        if not isinstance(cmd, str):
            raise ValueError(f"cmd must be of type string, but it was type {type(cmd)}")

        if self.tmux_enabled:
            await self._send_tmux_command_with_cmd_id(cmd, cmd_id)
        else:
            await self._send_shell_command_with_cmd_id(cmd, user, cmd_id)

        return cmd_id

    async def _send_shell_command_with_cmd_id(self, cmd: str, cmd_id: str, user: str) -> None:
        self.containers[0].exec_run(
            cmd=["sh", "-c", f"touch /tmp/{cmd_id}_out && touch /tmp/{cmd_id}_exit_code"], user=user
        )
        exec_run_cmd = f"{{ {cmd}; }} > /tmp/{cmd_id}_out 2>&1; echo $? > /tmp/{cmd_id}_exit_code"

        exec_id = self.docker_client.api.exec_create(
            self.containers[0].id,
            cmd=["sh", "-c", exec_run_cmd],
            user=user,
        )["Id"]
        self.docker_client.api.exec_start(exec_id, detach=True)

        self.cmd_id_to_exec_id[cmd_id] = exec_id

    async def _send_tmux_command_with_cmd_id(self, cmd: str, cmd_id: str) -> None:
        output = self.containers[0].exec_run(cmd=["tmux", "list-sessions"]).output.decode("utf-8")
        if cmd_id not in output:
            self.containers[0].exec_run(cmd=["tmux", "new", "-d", "-s", cmd_id])

        # Run command, redirect exit_code and output to files
        # TODO be mindful of edge cases here, make more robust in future
        self.containers[0].exec_run(f"touch /tmp/{cmd_id}_out && touch /tmp/{cmd_id}_exit_code")
        exec_run_cmd = f"{cmd} &> /tmp/{cmd_id}_out; echo $? > /tmp/{cmd_id}_exit_code"

        self.containers[0].exec_run(f"tmux send-keys -t {cmd_id}.0 '{exec_run_cmd}' Enter")

    def _upload_file_to_azure(
        self,
        file_path: str,
        account_name: str,
        container_name: str,
        blob_file_id: str,
        sas_token: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """
        Uploads a file on the host to azure.
        """
        # upload to azure
        cmd = f"az storage blob upload --account-name {account_name} --container-name {container_name} --name {blob_file_id} --file {file_path} --sas-token '{sas_token}'"
        if overwrite:
            cmd += " --overwrite"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        logger.info(
            f"Upload to Azure result: {result.stdout}, {result.stderr}, {result.returncode}"
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

    async def _start_periodic_task(
        self, interval: int, task: Callable[..., Awaitable[None]], *args: Any, **kwargs: Any
    ) -> asyncio.Task[None]:
        """
        A helper function to run another function periodically.
        """

        async def loop(*args: Any, **kwargs: Any) -> None:
            while True:
                try:
                    await task(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in periodic task {task.__name__}: {e}")
                await asyncio.sleep(interval)

        periodic_task = asyncio.create_task(loop(*args, **kwargs))
        return periodic_task

    async def upload_agent_logs(
        self,
        sources: list[str],
        blob_dir: str,
        account_name: str,
        container_name: str,
        sas_token: str,
    ) -> None:
        """
        Tars all source directories and files into a single tarball and uploads it to the storage account.
        """
        logger.info("[upload_task] proceeding")
        timestamp = time.strftime("%Y-%m-%dT%H-%M-%S-%Z", time.gmtime())
        blob_file_id = Path(blob_dir) / f"{timestamp}.tar.gz"
        container_tmp_dir = Path("/tmp") / f"{timestamp}"
        container_tar_path = Path("/tmp") / f"{timestamp}.tar.gz"
        # copy all the sources to a tmp dir and tar it
        self.containers[0].exec_run(cmd=["mkdir", "-p", str(container_tmp_dir)])
        for source in sources:
            self.containers[0].exec_run(cmd=["cp", "-r", str(source), str(container_tmp_dir)])
        logger.info("[upload_task] tarring")
        # tar "/tmp/{timestamp}" into "/tmp/{timestamp}.tar.gz", such that when we extract it, we just get "{timestamp}/"
        exit_code, output = self.containers[0].exec_run(
            cmd=[
                "tar",
                "-czvf",
                str(container_tar_path),
                "-C",
                str(container_tar_path.parent),
                timestamp,
            ]
        )
        logger.info(f"[upload_task] Tar result (exit code: {exit_code}): {output}")
        # upload the tarball to azure
        upload_cmd = f"az storage blob upload --account-name {account_name} --container-name {container_name} --name {str(blob_file_id)} --file {str(container_tar_path)} --sas-token '{sas_token}'"
        exit_code, output = self.containers[0].exec_run(cmd=upload_cmd)
        logger.info(f"[upload_task] Upload to Azure result (exit code: {exit_code}): {output}")

    async def upload_status_and_agent_log(
        self,
        machine_id: str,
        cmd_id: str,
        blob_dir: str,
        account_name: str,
        container_name: str,
        sas_token: str,
    ) -> None:
        """
        Uploads the current status and agent_run.log once to the storage account.
        """
        # Upload status.json
        status = {
            "machine_id": machine_id,
            "status": self.status,
            "created_at": cast(int, self.created_at),  # type: ignore
            "agent_finished_at": cast(int, self.agent_finished_at),  # type: ignore
            "last_updated": int(time.time()),
        }
        status_file = "/tmp/status.json"
        with open(status_file, "w") as f:
            json.dump(status, f, sort_keys=True)
        blob_file_path = Path(blob_dir) / "status.json"
        self._upload_file_to_azure(
            file_path=status_file,
            account_name=account_name,
            container_name=container_name,
            blob_file_id=str(blob_file_path),
            sas_token=sas_token,
            overwrite=True,
        )

        # Upload agent_run.log
        try:
            result = await self.send_shell_command_get_result(cmd_id, allow_unfinished=True)
        except AlcatrazOutOfDiskSpaceError as e:
            logger.error(f"Out of disk space, cannot check status of command {cmd_id}!\n{e}")
            result = {
                "running": False,
                "exit_code": 0,
                "result": "",
            }
        agent_log_file = "/tmp/agent_run.log"
        with open(agent_log_file, "w") as f:
            f.write(
                f"""Running: {result["running"]}\nExit Code: {result["exit_code"]}\n--- OUTPUT ---\n{result["result"]}"""
            )
        blob_file_path = Path(blob_dir) / "agent_run.log"
        self._upload_file_to_azure(
            file_path=agent_log_file,
            account_name=account_name,
            container_name=container_name,
            blob_file_id=str(blob_file_path),
            sas_token=sas_token,
            overwrite=True,
        )

    async def start_periodic_status_update_and_upload(
        self,
        machine_id: str,
        cmd_id: str,
        sources: list[str],
        account_name: str,
        container_name: str,
        blob_dir: str,
        sas_token: str,
        interval: int,
    ) -> None:
        """
        Uploads the current status and agent_run.log to the storage account every interval seconds.
        """

        async def upload_task(
            sources: list[str],
            account_name: str,
            container_name: str,
            blob_dir: str,
            sas_token: str,
        ) -> None:
            """
            Uploads agent logs whilst command hasn't finished running, then uploads one final time when command
            is done
            """
            # Get run status
            try:
                done = await self.send_shell_command_is_done(cmd_id)
            except AlcatrazOutOfDiskSpaceError as e:
                logger.error(f"Out of disk space, cannot check status of command {cmd_id}!\n{e}")
                done = True

            logger.info(f"[STATUS UPDATE] is send shell command done yet? {done}")
            if done:
                self.status = "done"
                if self.agent_finished_at is None:  # type: ignore
                    self.agent_finished_at = int(time.time())

                # Continue to upload the tarball until the agent is done, and then we upload one last time.
                logger.info("[upload_task] We're starting the upload task")
                if self.completed_final_upload:  # type: ignore
                    logger.info(
                        "Agent is done and we've already uploaded the final tarball, skipping upload_task"
                    )
                    return
                else:
                    logger.info(
                        "Agent is done but we haven't uploaded the final tarball yet, will do one last upload"
                    )
                    self.completed_final_upload = True

            await self.upload_agent_logs(sources, blob_dir, account_name, container_name, sas_token)

        async def upload_and_status_update_task(
            machine_id: str,
            cmd_id: str,
            sources: list[str],
            account_name: str,
            container_name: str,
            blob_dir: str,
            sas_token: str,
        ) -> None:
            await upload_task(sources, account_name, container_name, blob_dir, sas_token)
            await self.upload_status_and_agent_log(
                machine_id, cmd_id, blob_dir, account_name, container_name, sas_token
            )

        # need to install az cli on the container
        result = await self.send_shell_command("command -v az")
        if result["exit_code"] != 0:
            logger.info("azure-cli not found. Attempting to install it via pip...")
            result = await self.send_shell_command("pip install azure-cli")
            assert (
                result["exit_code"] == 0
            ), f"Failed to install azure-cli via pip: {result['result'].decode('utf-8', errors='replace')}"
            logger.info("successfully installed azure-cli via pip")
        else:
            logger.info("azure-cli is already installed.")

        # then, kick off tasks
        self.status = "running"
        self.completed_final_upload = False
        self.agent_finished_at = None  # type: ignore
        self.created_at = int(time.time())

        periodic_task = await self._start_periodic_task(
            interval,
            upload_and_status_update_task,
            machine_id,
            cmd_id,
            sources,
            account_name,
            container_name,
            blob_dir,
            sas_token,
        )
        self.periodic_upload_task = periodic_task

    async def stop_periodic_status_update_and_upload(self) -> None:
        try:
            self.periodic_upload_task.cancel()
        except Exception as e:
            logger.error(f"Error stopping periodic upload task:\n{e}")


garbage_collector_leader_lock_path = Path.home() / ".alcatraz"
docker_resource_locks_folder_path = (
    Path.home() / ".alcatraz" / "local_cluster_docker_resource_locks"
)
os.makedirs(docker_resource_locks_folder_path, exist_ok=True)


async def async_subprocess_run(cmd: list[str], timeout: float | None = 30.0) -> None:
    if not timeout:
        timeout = 0.0
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(process.stdout.readline()),  # type: ignore
                asyncio.create_task(process.stderr.readline()),  # type: ignore
            ],
            return_when=asyncio.ALL_COMPLETED,
        )

        logger.info((await list(done)[0]).decode())
        if len(done) > 1:
            logger.info((await list(done)[1]).decode())
    except asyncio.TimeoutError as e:
        process.kill()
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout) from e

    return_code = await process.wait()
    if return_code != 0:
        stderr = (
            (await list(pending)[0]).decode()
            if pending
            else "" + (await process.stderr.read()).decode()  # type: ignore
        )
        logger.error(stderr)
        stdout = (await process.stdout.read()).decode()  # type: ignore
        raise subprocess.CalledProcessError(
            returncode=return_code, cmd=cmd, output=stdout, stderr=stderr
        )


class LocalCluster(BaseAlcatrazCluster):
    def __init__(
        self,
        image: str,
        side_images: list[str] | None = None,
        runtime: str | None = None,
        docker_host: str = "unix:///var/run/docker.sock",
        pull_from_registry: bool = True,
        local_network: bool = False,
        health_check: bool = False,
        jupyter_setup: list[str] | None = None,
        is_nvidia_gpu_env: bool = False,  # you better have nvidia gpus on your machine if you use this
        privileged: bool = False,
        environment: dict[str, str] | None = None,
        disk_mount_path: str | None = None,
        azure_container_config: dict[str, str] | None = None,
        azure_files_config: dict[str, Any] | None = None,
        volumes_config: VolumesConfig | None = None,
        shm_size: str | None = None,
        mem_limit: str | None = None,
        limits: Limits = DEFAULT_LIMITS,
        container_registry_credentials: ContainerRegistryCredentials | None = None,
        docker_compose_yaml: str | None = None,
        tmux_enabled: bool = False,
    ):
        if jupyter_setup is None:
            jupyter_setup = ["jupyter", "kernel", "--ip", "0.0.0.0"]
        super().__init__(
            main_image=image,
            side_images=side_images if side_images else [],
            runtime=runtime,
            pull_from_registry=pull_from_registry,
            health_check=health_check,
            local_network=local_network,
            jupyter_setup=jupyter_setup,
            privileged=privileged,
            container_registry_credentials=container_registry_credentials,
            docker_compose_yaml=docker_compose_yaml,
            tmux_enabled=tmux_enabled,
            docker_host=docker_host,
        )
        self.tmux_enabled = tmux_enabled
        self.docker_host = docker_host
        self.main_image = image
        self.side_images = side_images if side_images else []
        self.pull_from_registry = pull_from_registry
        self.health_check = health_check
        self.local_network = local_network
        self.jupyter_setup = jupyter_setup
        self.is_nvidia_gpu_env = is_nvidia_gpu_env
        self.privileged = privileged
        self.environment = environment
        self.docker_compose_yaml = docker_compose_yaml

        self.disk_mount_path = disk_mount_path
        self.azure_files_config = azure_files_config
        self.azure_container_config = azure_container_config
        self.volumes_config = volumes_config

        self.shm_size = shm_size
        self.mem_limit = mem_limit

        self.limits = limits

        if self.disk_mount_path:
            logger.info(f"Mounting disk at {disk_mount_path}...")

            command = (
                "lsblk -o NAME,SIZE,TYPE | grep '4T' | grep 'part' | awk '{print $1}'"  # TODO dont
            )
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            device = result.stdout.strip().replace("└─", "")
            logger.info(f"Device is found on: {device}")

            logger.info("%s", subprocess.run(["sudo", "mkdir", "-p", cast(str, disk_mount_path)]))
            logger.info(
                "%s",
                subprocess.run(["sudo", "mount", f"/dev/{device}", cast(str, disk_mount_path)]),
            )

        if azure_files_config:
            logger.info(
                f"Mounting Azure Files from {azure_files_config['fileshare_data_path']} (on Azure Files) to {azure_files_config['mount_dest']}"
            )
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "cifs-utils"], check=True)

            # Make dest
            logger.info(
                "%s",
                subprocess.run(
                    ["sudo", "mkdir", "-p", cast(str, azure_files_config["mount_dest"])], check=True
                ),
            )
            # Create credentials file
            cmd = f"sudo mkdir -p '/etc/smbcredentials' && bash -c \"echo -e 'username={azure_files_config['username']}\npassword={azure_files_config['password']}' | sudo tee /etc/smbcredentials/kaggledisks.cred\" && sudo chmod 600 /etc/smbcredentials/kaggledisks.cred"
            logger.info(
                "%s", subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            )
            # Mount to az file storage
            cmd = f"sudo mount -t cifs {azure_files_config['SMB_PATH']} {azure_files_config['mount_dest']} -o credentials=/etc/smbcredentials/kaggledisks.cred,serverino,nosharesock,actimeo=30,mfsymlinks"
            logger.info(
                "%s", subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            )

            # Download tar files on the VM to save image pull time
            if (
                "azure_files_tar_path" in azure_files_config
                and "os_tar_path" in azure_files_config
                and "os_data_path" in azure_files_config
            ):
                azure_files_tar_path = azure_files_config["azure_files_tar_path"]
                os_tar_path = azure_files_config["os_tar_path"]
                os_data_path = azure_files_config["os_data_path"]

                download_tarfiles_cmds = [
                    f"time cp {azure_files_tar_path} {os_tar_path}",
                    f"sudo mkdir -p {os_data_path}",
                    f"time tar -xf {os_tar_path} -C {os_data_path}",
                    f"time rm {os_tar_path}",
                ]

                for cmd in download_tarfiles_cmds:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, check=True
                    )
                    logger.info(result)

        if azure_container_config:
            assert "url" in azure_container_config
            assert "tar_dest" in azure_container_config
            assert "os_dest" in azure_container_config

            url = azure_container_config["url"]
            tar_dest = azure_container_config["tar_dest"]
            os_dest = azure_container_config["os_dest"]

            logger.info(
                f"Downloading blobstore data from {url} to {tar_dest} and extracting to {os_dest}"
            )

            bash_cmds = [
                "sudo bash -c 'cd /usr/local/bin; curl -L https://aka.ms/downloadazcopy-v10-linux | tar --strip-components=1 --exclude=*.txt -xzvf -; chmod +x azcopy'",
                f"time azcopy copy '{url}' '{tar_dest}'",
                f"sudo mkdir -p {os_dest}",
                f"time tar -xf {tar_dest} -C {os_dest}",
                f"time rm {tar_dest}",
            ]

            for cmd in bash_cmds:
                try:
                    logger.info(f"command: {cmd}")
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    logger.info(f"result: {result.stdout}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error running command: {cmd}")
                    logger.error(f"Command output: {e.stdout}")
                    logger.error(f"Command error: {e.stderr}")
                    raise e

    @override
    async def _get_docker_client(self) -> DockerClient:
        try:
            docker_client = docker.from_env(
                environment={"DOCKER_HOST": self.docker_host},
                max_pool_size=1000,
                timeout=self.limits["docker_client_timeout_seconds"],
            )
        except docker.errors.DockerException as e:
            if "No such file or directory" in str(e):
                raise RuntimeError(
                    "Couldn't connect to local docker engine. Are you sure it's running?"
                ) from e
            else:
                raise e
        try:
            # Ever make a docker container and forget to delete it??
            # Our Garbage collector takes care of that for you
            # We heavily use unix file locks to achieve this
            # An individual LocalCluster is elected the leader by taking a lock on the leader lock (this current try catch block)
            # The leader is in charge of cleaning up old docker resources and lock files
            # Every other LocalCluster just has to hold a lock on a single file to indicate the LocalCluster instance is still using the docker resources associated with it. LocalCluster instances *should* clean up the docker resources themselves, but if they don't then the leader will.
            garbage_collector_leader_lock = UnixFileLock(
                garbage_collector_leader_lock_path
                / ((await asyncio.to_thread(docker_client.info))["ID"] + ".lock")
            )
            leader_lock = garbage_collector_leader_lock.acquire(blocking=False)
            logger.info("Acquired gc leader lock %s", garbage_collector_leader_lock.lock_file)

            self._exit_stack.callback(
                asyncio.create_task(
                    self._garbage_collector_leader_resource_cleanup(docker_client)
                ).cancel
            )
            self._exit_stack.callback(leader_lock.lock.release)
        except LockTimeout:
            # The current LocalCluster instance is not the leader!
            pass
        # lock docker resources for the current LocalCluster instance
        resource_lock = UnixFileLock(
            docker_resource_locks_folder_path / (self.container_group_name + ".lock")
        ).acquire(blocking=False)
        self._exit_stack.callback(resource_lock.lock.release)
        self._exit_stack.callback(
            lambda: Path(resource_lock.lock.lock_file).unlink(missing_ok=True)
        )
        return docker_client

    async def _garbage_collector_leader_resource_cleanup(self, docker_client: DockerClient) -> None:
        while True:
            start_time = time.time()
            nets_on_disk = {
                "tinydockernet-" + n.name.split(".lock")[0]
                for n in docker_resource_locks_folder_path.iterdir()
            }
            nets = [
                net
                for net in docker_client.networks.list()
                if cast(str, net.name).startswith("tinydockernet-alcatraz-")
                and cast(str, net.name) not in nets_on_disk
            ]  # type: ignore
            await asyncio.gather(
                *[asyncio.to_thread(self._garbage_collect_net, net) for net in nets]
            )
            await asyncio.gather(
                *[
                    asyncio.to_thread(self._garbage_collect_net_disk, ntwk, docker_client)
                    for ntwk in docker_resource_locks_folder_path.iterdir()
                ]
            )
            await asyncio.sleep(max(0, 60 - (time.time() - start_time)))

    @staticmethod
    def _garbage_collect_net(net: Network) -> None:
        net.reload()
        logger.info(f"[garbage-collector] Removing {net.name} with containers {net.containers}")
        for container in net.containers:
            try:
                container.remove(force=True)
            except Exception:
                logger.error(
                    f"[garbage-collector] failed to remove {container.name} , maybe this container is in multiple networks?"
                )
        try:
            net.remove()
        except Exception:
            logger.error(
                f"[garbage-collector] failed to remove {net.name} with containers {net.containers}"
            )

    @staticmethod
    def _garbage_collect_net_disk(ntwk: Path, docker_client: DockerClient) -> None:
        # TODO this leads to
        # urllib3 Connection pool is full, discarding connection: localhost. Connection pool size: 10 error
        # fixing this with an environment variable temporarily

        if os.environ.get("ALCATRAZ_SKIP_GC_DISK"):
            return

        # if we can aquire a lock, kill the docker resources
        should_remove_file = False
        try:
            with UnixFileLock(ntwk, timeout=0):
                should_remove_file = True
                logger.info(f"[garbage-collector] Removing {ntwk.name} lock's resources")
                try:
                    net = docker_client.networks.get("tinydockernet-" + ntwk.name.split(".lock")[0])
                    net.reload()
                    for container in net.containers:
                        container.remove(force=True)
                    net.remove()
                except docker.errors.NotFound:
                    logger.info(f"[garbage-collector] Network {ntwk.name} not found")
                    pass
        except LockTimeout:
            pass
        if should_remove_file:
            ntwk.unlink(missing_ok=True)

    @override
    def serialize(self) -> ClusterConfig:
        raise NotImplementedError("LocalCluster cannot be serialized")
