# mypy: ignore-errors
import asyncio
import base64
import builtins
import functools
import inspect
import json
import logging
import os
import resource
import socket
import threading
import time
from enum import StrEnum
from pprint import pformat
from typing import Awaitable, Callable, Self, cast
from uuid import uuid4
from weakref import WeakKeyDictionary

import blobfile
import httpx
import msgpack
import structlog.stdlib
import tenacity
from alcatraz.clusters._serialization import SerializableBaseModel
from alcatraz.clusters.interface import AlcatrazException
from alcatraz.clusters.local import (
    DEFAULT_LIMITS,
    BaseAlcatrazCluster,
    ClusterConfig,
    ContainerRegistryCredentials,
    Limits,
    VolumesConfig,
)
from alcatraz.server.swarm.worker.worker import decode_extras, encode_extras
from typing_extensions import override

# GitHub Actions does not permit calling resource.setrlimit, so we only call it if we're not in CI
# We won't be testing SwarmCluster in CI anyway, so this is fine.
# We still need to do this because it happens at import time, so it affects non-swarm tests that
# include a swarm import.
if os.environ.get("CI") != "true":
    resource.setrlimit(
        resource.RLIMIT_NOFILE, (131_072, 131_072)
    )  # allow more tcp connections open at once. Default is O(1K) as verified by resource.getrlimit(resource.RLIMIT_NOFILE)
DEFAULT_SWARM_API_SERVER_HOST = "swarm-api-server.alcatraz.openai.org"
DEFAULT_SWARM_PROXY_SERVER_HOST = "swarm-proxy.alcatraz.openai.org"
DEFAULT_SWARM_PORT_FORWARD_HOST = "port-forward.alcatraz.openai.org"
GPU_SKUS = {
    "Standard_NC4as_T4_v3",
    "Standard_NC6s_v3",
    "Standard_NC24ads_A100_v4",
    "Standard_NV18ads_A10_v5",
    "Standard_NV36ads_A10_v5",
    "Standard_NV72ads_A10_v5",
}  # incomplete list, add anything as needed

rate_limiting_id = str(uuid4())

logger = structlog.stdlib.get_logger(component=__name__)


# Heartbeats must happen at least every 10 minutes, else Alcatraz will delete the machine on the server side.
_HEARTBEAT_TIMEOUT_SECONDS = 600
_HEARTBEAT_INTERVAL_SECONDS = _HEARTBEAT_TIMEOUT_SECONDS // 2


_http_clients: WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient] = WeakKeyDictionary()


async def _per_event_loop_httpx_client() -> httpx.AsyncClient:
    # We use a shared httpx client across all swarm clusters in the same event loop. Note that
    # AsyncClient is thread safe but not safe across multiple event loops, so we have to shard
    # per event loop rather than per process.
    # We do this because we need to limit the maximum number of open connections from one client IP (all of
    # research shares one IP) to the swarm API server, so it's very important to reuse
    # connections.
    loop = asyncio.get_running_loop()

    # note: locking isn't necessary because it's not a big deal to make another httpx
    # client, subsequent calls to this function will just return the same client
    if loop not in _http_clients:
        _http_clients[loop] = await httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(
                # Azure Load Balancer has a 4min timeout, but some HTTP calls take
                # >4 minutes. The workaround is to enable TCP keep alive, which is
                # somewhat unusual, but it requires no code changes.
                socket_options=_keep_alive_socket_options(),
                limits=httpx.Limits(max_keepalive_connections=None, max_connections=None),
            ),
            # Disable all timeouts. Alcatraz client is expected to enforce timeouts.
            timeout=None,
        ).__aenter__()

    return _http_clients[loop]


class AlcatrazTransientRuntimeError(AlcatrazException):
    """
    Errors due to Swarm infra problems in Swarm client side and/or serverside code. You probably want to retry your rollout from scratch.
    """

    pass


class AlcatrazUnknownError(AlcatrazTransientRuntimeError):
    """
    Swarm errors of unknown cause. Probably due to implementation bugs in alcatraz.
    """

    pass


class AlcatrazAuthError(RuntimeError):
    """Errors related to authx"""


def get_user_ssh_key() -> str:
    ssh_dir = os.path.expanduser("~/.ssh")
    oai_key_path = os.path.join(ssh_dir, "oai.pub")
    rsa_key_path = os.path.join(ssh_dir, "id_rsa.pub")

    if os.path.exists(oai_key_path):
        with open(oai_key_path, "r") as file:
            return file.read().strip()
    elif os.path.exists(rsa_key_path):
        with open(rsa_key_path, "r") as file:
            return file.read().strip()
    else:
        logger.warning("No recognized SSH public key found. ([oai.pub] or [id_rsa.pub])")
        return ""


def blob_write(pth: str, content: str) -> None:
    with blobfile.BlobFile(pth, "w") as f:
        f.write(content)


def _keep_alive_socket_options() -> list[tuple[int, int, int]]:
    options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    if hasattr(socket, "TCP_KEEPIDLE"):
        # linux
        options.extend(
            [
                # Send a keepalive packet every 60s, after 60s of inactivity, fail after 1st error
                (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60),  # type: ignore
                (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60),
                (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 1),
            ]
        )
    elif hasattr(socket, "TCP_KEEPALIVE"):
        # macos
        options.extend(
            [
                (socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 60),  # type: ignore
            ]
        )
    else:
        raise NotImplementedError("OS does not support TCP keepalive?")

    return options  # type: ignore


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(
        AlcatrazTransientRuntimeError
    ),  # cat /proc/sys/net/ipv4/tcp_fin_timeout on devbox is 60 seconds so it's prudent to reuse TCP connections. You can use netstat -an | grep TIME_WAIT | wc -l on a devbox to track number of ports stuck in TIME_WAIT state
    wait=tenacity.wait_random_exponential(multiplier=1, max=60),
    before_sleep=tenacity.before_sleep_log(
        cast(logging.Logger, logger), logging.WARNING, exc_info=False
    ),
    reraise=True,
)
async def _httpx_post(client: httpx.AsyncClient, *args, **kwargs):
    try:
        transport = client._transport
        # may be a wrapped AsyncOpenTelemetryTransport
        if isinstance(transport, httpx.AsyncHTTPTransport):
            logger.debug("Open connections: %d", len(transport._pool.connections))
        return await client.post(*args, **kwargs)
    except httpx.TransportError as e:
        logger.debug("Hit a {e} error in _httpx_post")
        raise AlcatrazTransientRuntimeError("Failed httpx post") from e


class _SwarmClusterState(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    CLOSED = "CLOSED"


class SerializationExtras(SerializableBaseModel):
    # state to resume from
    machine_info: str
    last_heartbeat_timestamp: float


class SwarmConfig(ClusterConfig):
    # config
    azure_vm_sku: str = "Standard_D2as_v4"
    api_server_host: str = DEFAULT_SWARM_API_SERVER_HOST
    proxy_server_host: str = DEFAULT_SWARM_PROXY_SERVER_HOST
    namespace: str = os.getenv("ALCATRAZ_NAMESPACE", "shared")
    blob_storage_folder_for_logs: str | None = None
    privileged: bool = False
    kill_machine_on_exit: bool = True
    runtime: str | None = None

    # Bind volumes
    volumes_config: VolumesConfig | None = None
    disk_mount_path: str | None = None

    # Docker limits
    shm_size: str | None = None
    mem_limit: str | None = None
    limits: Limits = DEFAULT_LIMITS

    # Container registry credentials
    container_registry_credentials: ContainerRegistryCredentials | None = None

    # state to resume from
    serialization_extras: SerializationExtras | None = None

    @override
    def build(self) -> "SwarmCluster":
        return SwarmCluster(
            image=self.image,
            side_images=self.side_images,
            runtime=self.runtime,
            blob_storage_folder_for_logs=self.blob_storage_folder_for_logs,
            azure_vm_sku=self.azure_vm_sku,
            api_server_host=self.api_server_host,
            proxy_server_host=self.proxy_server_host,
            kill_machine_on_exit=self.kill_machine_on_exit,
            privileged=self.privileged,
            serialization_extras=self.serialization_extras,
            disk_mount_path=self.disk_mount_path,
            azure_files_config=self.azure_files_config,
            azure_container_config=self.azure_container_config,
            volumes_config=self.volumes_config,
            shm_size=self.shm_size,
            mem_limit=self.mem_limit,
            environment=self.environment,
            limits=self.limits,
            container_registry_credentials=self.container_registry_credentials,
            namespace=self.namespace,
            jupyter_setup=self.jupyter_setup,
            docker_compose_yaml=self.docker_compose_yaml,
            tmux_enabled=self.tmux_enabled,
        )


@functools.cache
def _load_remote_semaphore(concurrency: int) -> asyncio.Semaphore:
    return asyncio.Semaphore(concurrency)


class SwarmCluster(BaseAlcatrazCluster):
    """Machines created here run any docker image you want with no internet access.
    You can also specify side containers which share a docker network with the main container.
    The way this works is that we request a remote VM, we upload LocalCluster's code to it, then we forward all SwarmCluster method calls to the remote LocalCluster instance
    """

    def __init__(
        self,
        image: str,
        side_images: list[str] | None = None,
        runtime: str | None = None,
        blob_storage_folder_for_logs: str | None = None,
        azure_vm_sku: str = "Standard_D2as_v4",
        api_server_host: str = DEFAULT_SWARM_API_SERVER_HOST,
        proxy_server_host: str = DEFAULT_SWARM_PROXY_SERVER_HOST,
        kill_machine_on_exit: bool = True,
        privileged: bool = False,
        serialization_extras: SerializationExtras | None = None,
        environment: dict[str, str] | None = None,
        disk_mount_path: str | None = None,
        azure_files_config: dict[str, str] | None = None,
        azure_container_config: dict[str, str] | None = None,
        volumes_config: VolumesConfig | None = None,
        on_enter: Callable[[str], Awaitable[None]] | None = None,
        on_exit: Callable[[str], Awaitable[None]] | None = None,
        shm_size: str | None = None,
        mem_limit: str | None = None,
        limits: Limits = DEFAULT_LIMITS,
        jupyter_setup: list[str] | None = None,
        idempotency_expiry: int = 30 * 60,  # 30 minutes
        quota_project_key: str | None = os.getenv(  # deprecated
            "ALCATRAZ_QUOTA_PROJECT_API_KEY", None
        ),  #  format is <project_name>/<api_key>
        namespace: str = os.getenv("ALCATRAZ_NAMESPACE", "shared"),
        container_registry_credentials: ContainerRegistryCredentials | None = None,
        docker_compose_yaml: str | None = None,
        tmux_enabled: bool = False,
    ):
        if jupyter_setup is None:
            jupyter_setup = ["jupyter", "kernel", "--ip", "0.0.0.0"]
        if side_images is None:
            side_images = []
        assert len(side_images) < 60
        assert image.count(":") == 1
        self.main_image = image
        self.side_images = side_images
        self.runtime = runtime
        if blob_storage_folder_for_logs:
            assert blob_storage_folder_for_logs.startswith("az://")
            assert (
                blob_storage_folder_for_logs.count("/") >= 3
            ), "missing storage account or container"
            self.blob_storage_folder_for_logs = blob_storage_folder_for_logs.rstrip("/")
            logger.info(f"Swarm logging to {blob_storage_folder_for_logs}")
        else:
            self.blob_storage_folder_for_logs = None
        assert azure_vm_sku.strip()
        self.azure_vm_sku = azure_vm_sku
        self.is_nvidia_gpu_env = azure_vm_sku in GPU_SKUS
        self.api_server_host = api_server_host
        self.proxy_server_host = proxy_server_host
        self.privileged = privileged
        self.disk_mount_path = disk_mount_path
        self.environment = environment
        self.docker_compose_yaml = docker_compose_yaml

        # volumes_config is a dict of dicts, each dict must have keys "bind_dest" and "bind_source"
        self.volumes_config = volumes_config

        self.azure_files_config = azure_files_config
        self.azure_container_config = azure_container_config
        if azure_files_config:
            assert "username" in azure_files_config, f"Missing username in {azure_files_config}"
            assert "password" in azure_files_config, f"Missing password in {azure_files_config}"
            assert "SMB_PATH" in azure_files_config, f"Missing SMB_PATH in {azure_files_config}"
            assert "mount_dest" in azure_files_config, f"Missing mount_dest in {azure_files_config}"
            assert (
                "fileshare_data_path" in azure_files_config
            ), f"Missing fileshare_data_path in {azure_files_config}"

        self.quota_project_key = quota_project_key
        assert (
            namespace
        ), "namespace is empty. Set ALCATRAZ_NAMESPACE env var or use `shared` namespace"
        self.namespace = namespace

        self.on_enter = on_enter
        self.on_exit = on_exit

        self._state = _SwarmClusterState.UNINITIALIZED
        self.kill_machine_on_exit = kill_machine_on_exit
        self.serialization_extras = serialization_extras

        self.shm_size = shm_size
        self.mem_limit = mem_limit

        self.limits = limits
        self.idempotency_expiry = idempotency_expiry
        self.container_registry_credentials = container_registry_credentials
        self.swarm_metrics = {}
        self.tmux_enabled = tmux_enabled

        super().__init__(
            image,
            side_images if side_images else [],
            is_nvidia_gpu_env=self.is_nvidia_gpu_env,
            privileged=self.privileged,
            runtime=self.runtime,
            limits=self.limits,
            container_registry_credentials=container_registry_credentials,
            jupyter_setup=jupyter_setup,
            docker_compose_yaml=docker_compose_yaml,
            tmux_enabled=tmux_enabled,
        )  # TODO The args passed in here literally dont matter. There's 0 reason for SwarmCluster to subclass BaseAlcatrazCluster

    async def _get_docker_client(self):
        raise NotImplementedError()  # not needed for swarm

    @override
    def serialize(self) -> SwarmConfig:
        # Note: We allow serialize even if kill_machine_on_exit is True because in qstar, we need to serialize and
        # reopen a cluster in the Grader even though it's still being held open (and eventually will be killed) in the
        # Toolbox.

        if self._state != _SwarmClusterState.INITIALIZED:
            assert self.serialization_extras

        return SwarmConfig(
            image=self.main_image,
            side_images=self.side_images,
            azure_vm_sku=self.azure_vm_sku,
            api_server_host=self.api_server_host,
            proxy_server_host=self.proxy_server_host,
            blob_storage_folder_for_logs=self.blob_storage_folder_for_logs,
            privileged=self.privileged,
            kill_machine_on_exit=self.kill_machine_on_exit,
            serialization_extras=(
                SerializationExtras(
                    machine_info=self.machine_info,
                    last_heartbeat_timestamp=self.last_heartbeat_timestamp,
                )
                if self._state == _SwarmClusterState.INITIALIZED
                else self.serialization_extras
            ),
            azure_files_config=self.azure_files_config,
            azure_container_config=self.azure_container_config,
            docker_compose_yaml=self.docker_compose_yaml,
            tmux_enabled=self.tmux_enabled,
        )

    async def _start(self) -> None:
        assert (
            self._state == _SwarmClusterState.UNINITIALIZED
        ), "_start was already called on this SwarmCluster instance"
        start_time = time.time()
        self._httpx_client = await _per_event_loop_httpx_client()
        if self.serialization_extras:
            self.machine_info = self.serialization_extras.machine_info
            logger.info("Already using machine %s", self.machine_info)
            self.last_heartbeat_timestamp = self.serialization_extras.last_heartbeat_timestamp
            self._check_heartbeat_status()
            loop = asyncio.get_running_loop()
            logger.debug(
                f"Creating heartbeat task in thread: {threading.current_thread().name} using loop: {loop}, loop id: {id(loop)} "
            )
            self._exit_stack.callback(asyncio.create_task(self._heartbeat()).cancel)
        else:
            await self._claim_machine()
            logger.info(f"Claimed machine {self.machine_info}")
            self.swarm_metrics["SwarmCluster:claim_machine_time"] = time.time() - start_time
            self.last_heartbeat_timestamp = (
                time.time()
            )  # NOTE: super long docker pull in _remote_load_module will cause machine to die from lack of heartbeat. So we start heartbeat before _remote_load_module. We also have it here so that it starts when desearlizing a SwarmCluster object
            loop = asyncio.get_running_loop()
            logger.debug(
                f"Creating heartbeat task in thread: {threading.current_thread().name} using loop: {loop}, loop id: {id(loop)} "
            )
            self._exit_stack.callback(asyncio.create_task(self._heartbeat()).cancel)
            await self._remote_load_module()
            self.swarm_metrics["SwarmCluster:load_module_time"] = (
                time.time() - self.swarm_metrics["SwarmCluster:claim_machine_time"] - start_time
            )
            logger.info("Loaded remote modules")

        if self.kill_machine_on_exit:
            self._exit_stack.push_async_callback(self._kill_machine)

        if self.blob_storage_folder_for_logs:
            await self._save_logs_to_blob_storage()  # run once here so errors propagate up
            self._exit_stack.push_async_callback(self._save_logs_to_blob_storage)
        self._state = _SwarmClusterState.INITIALIZED

    async def _kill_machine(self) -> None:
        res = await _httpx_post(
            self._httpx_client,
            f"http://{self.api_server_host}/kill_machines/",
            params={"scaleset_machineid_ips": self.machine_info},
        )
        if res.status_code in (200, 404):
            return
        res.raise_for_status()

    async def _stop(self) -> None:
        self._state = _SwarmClusterState.CLOSED
        self._closed_reason = "manually"
        await self._exit_stack.aclose()

    async def __aenter__(self) -> Self:
        try:
            await self._start()
            if self.on_enter:
                logger.info("Executing `on_enter` callback function...")
                await self.on_enter(self.machine_info)
        except Exception as e:
            raise AlcatrazException("Failed to start SwarmCluster") from e
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        # i'm not sure this logging was a good idea. it's log spam and often confusing. But sometimes it does give us hints we wouldn't otherwise have had... hmmmmm
        # if exc_type is not None:
        #     logger.error(
        #         "An exception occurred in the SwarmCluster context manager!",
        #         exc_info=(exc_type, exc_value, exc_tb),  # type: ignore
        #     )

        try:
            if self.on_exit:
                logger.info("Executing `on_exit` callback function...")
                await self.on_exit(self.machine_info)
            await self._stop()
        except Exception as e:
            raise AlcatrazException("Failed to stop SwarmCluster") from e

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(AlcatrazTransientRuntimeError),
        wait=tenacity.wait_random_exponential(multiplier=1, max=120),
        before_sleep=tenacity.before_sleep_log(logger.bind(), logging.WARNING, exc_info=True),
        reraise=True,
    )
    async def _claim_machine(self):
        response = await _httpx_post(
            self._httpx_client,  # TODO use a connection global to the process to decrease # of TCP connections on api server. If you ever want to go past 50K per minute churn!
            f"http://{self.api_server_host}/claim_machines/",
            params={
                "num_machines": 1,
                "untrusted_user_provided_id": rate_limiting_id,
                "user_provided_ssh_key": get_user_ssh_key(),
                "vm_sku": self.azure_vm_sku,
                "quota_project_key": self.quota_project_key,  # deprecated
                "namespace": self.namespace,
            },
        )
        if response.status_code == 429:
            raise AlcatrazTransientRuntimeError("Rate limited by swarm api server")
        response = response.json()
        if not response["claimed_machines"]:
            raise AlcatrazTransientRuntimeError(
                f"No machines available in swarm cluster for sku {self.azure_vm_sku}{(' for project '+self.quota_project_key.split('/')[0]+'/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' if self.quota_project_key else '')} for {self.namespace} namespace {json.dumps(response)}"
            )
        self.machine_info = response["claimed_machines"][0]

    async def _remote_load_module(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        files = {}
        # This list of files needs to be in import order - so local depends on everything
        # before it on the list
        for module_name in [
            "_vnc",
            "interface",
            "_serialization",
            "_certificate_authority",
            "_container_proc",
            "local",
        ]:
            with open(os.path.join(dir_path, module_name + ".py")) as f:
                files[f"alcatraz.clusters.{module_name}"] = f.read()

        init_args = {  # basically goes into a `LocalCluster(**init_args)` on a remote cloud VM
            "image": self.main_image,
            "side_images": self.side_images,
            "is_nvidia_gpu_env": self.is_nvidia_gpu_env,
            "privileged": self.privileged,
            "environment": self.environment,
            "disk_mount_path": self.disk_mount_path,
            "azure_files_config": self.azure_files_config,
            "azure_container_config": self.azure_container_config,
            "volumes_config": self.volumes_config,
            "shm_size": self.shm_size,
            "mem_limit": self.mem_limit,
            "limits": self.limits,
            "runtime": self.runtime,
            "container_registry_credentials": self.container_registry_credentials,
            "jupyter_setup": self.jupyter_setup,
            "docker_compose_yaml": self.docker_compose_yaml,
            "tmux_enabled": self.tmux_enabled,
        }

        logger.info("Initialization concurrency: %s", self.limits["initialization_concurrency"])
        async with _load_remote_semaphore(self.limits["initialization_concurrency"]):
            response = await _httpx_post(
                self._httpx_client,
                f"http://{self.proxy_server_host}/proxy/load_module",
                headers={
                    "x-idempotency-key": str(uuid4()),
                    "x-idempotency-expiry": str(self.idempotency_expiry),
                },
                json={
                    "machine_info": self.machine_info,
                    "init_args": init_args,
                    "code": files,
                    "pip_install": [
                        # if it has types that we'll serialize w pickle over the wire, use 3 parts of version number. otherwise 2 suffices
                        "docker==6.1",
                        "pillow",
                        "tenacity",
                        "filelock",
                        "jupyter-client==8.6",
                        "asyncvnc",
                        "vncdotool",
                        "requests==2.31",
                        # note: because worker.py uses fastapi which depends on pydantic, it's already loaded the wrong pydantic version so while this install does install correct pydantic version, the script hasn't stopped running so it continues to run the wrong pydantic version when it runs LocalCluster code. We handle this in worker.py by force reloading pydantic
                        # jk i couldnt get that working so instead i put the right pydantic version in the packer image... fragile :(
                        "pydantic==2.9.2",  # TODO how do i make these version numbers match oai laptop version numbers??
                        "typing-extensions==4.10.0",
                        "msgpack",
                        "cffi==1.16.0",
                        # "diskcache==5.6.3",
                        "PyYAML",
                    ],
                },
            )

        if response.status_code == 580:
            exc = response.json()
            if hasattr(builtins, exc["exception_type"]):
                # TODO support non builtin exceptions like docker exceptions etc
                assert issubclass(
                    getattr(builtins, exc["exception_type"]), Exception
                ), "cc @evanmays we only want to instantiate arbitrary class if it's an exception class. This assert is needed!"
                custom_exception = getattr(builtins, exc["exception_type"])(
                    exc["exception_message"]
                )
            else:
                custom_exception = type(exc["exception_type"], (Exception,), {})(
                    exc["exception_message"]
                )
            # custom_exception.__traceback__ = exc["exception_traceback"] # could cause problems
            logger.error(
                f"[worker] Error on remote worker {self.machine_info}:\n{exc['exception_traceback']}"
            )
            raise custom_exception
        elif response.status_code == 401:
            raise AlcatrazAuthError(
                f"You no longer own the VM with machine_info {self.machine_info} there is no hope in retrying this error"
            )
        elif response.status_code != 200:
            raise AlcatrazUnknownError(
                f"Error on remote swarm machine or proxy when setting up with response code {response.status_code}: "
                + response.text
                + f"\n\nMachine info:\n\n{self.machine_info}"
            )

    def _check_heartbeat_status(self) -> None:
        assert (
            time.time() - self.last_heartbeat_timestamp < _HEARTBEAT_TIMEOUT_SECONDS
        ), f"It's been {time.time() - self.last_heartbeat_timestamp} seconds since the last heartbeat was sent. The machine is likely dead now. You should use asyncio better and/or deserialize faster!!"
        logger.info(
            "Heartbeat is alive",
            time=time.time(),
            last_heartbeat_timestamp=self.last_heartbeat_timestamp,
            elapsed=time.time() - self.last_heartbeat_timestamp,
            id=repr(self),
        )

    async def _remote_proxy_method(self, method, *args, **kwargs):
        match self._state:
            case _SwarmClusterState.UNINITIALIZED:
                raise ValueError(
                    "A method on SwarmCluster instance was called but the instance is not initialized. Call __aenter__ or _start"
                )
            case _SwarmClusterState.INITIALIZED:
                pass
            case _SwarmClusterState.CLOSED:
                # This can be a user error, but it can also be a system error, e.g. if the machine crashes.
                # Thus we make it AlcatrazException.
                raise AlcatrazException(
                    f"A method on SwarmCluster instance was called but the instance was closed {self._closed_reason}"
                )
            case _:
                raise NotImplementedError()

        self._check_heartbeat_status()

        logger.debug(f"Proxy method invoked for: {method} with args: {args} and kwargs: {kwargs}")
        args = base64.b64encode(msgpack.packb(args, default=encode_extras)).decode("utf-8")  # type: ignore
        kwargs = base64.b64encode(msgpack.packb(kwargs, default=encode_extras)).decode("utf-8")  # type: ignore
        logger.debug("Proxy args pickled")
        # TODO if cancelled error raised here, then forward it to the server somehow... so server can raise cancellederror in LocalCluster
        response = await _httpx_post(
            self._httpx_client,
            f"http://{self.proxy_server_host}/proxy/call_method",
            json={
                "is_generator": False,
                "machine_info": self.machine_info,
                "method": method,
                "args": args,
                "kwargs": kwargs,
            },
            headers={
                "x-idempotency-key": str(uuid4()),
                "x-idempotency-expiry": str(self.idempotency_expiry),
            },
        )
        if response.status_code == 580:
            exc = response.json()
            try:
                if hasattr(builtins, exc["exception_type"]):
                    # TODO support non builtin exceptions like docker exceptions etc
                    assert issubclass(
                        getattr(builtins, exc["exception_type"]), Exception
                    ), "cc @evanmays we only want to instantiate arbitrary class if it's an exception class. This assert is needed!"
                    custom_exception = getattr(builtins, exc["exception_type"])(
                        exc["exception_message"]
                    )
                else:
                    custom_exception = type(exc["exception_type"], (Exception,), {})(
                        exc["exception_message"]
                    )
            except (TypeError, AssertionError) as e:
                # Sometimes building the exception can fail, e.g. TypeError function takes exactly 5 arguments (1 given)
                # In this case, we still raise but note the raw return value
                raise AlcatrazUnknownError(
                    "Failed to reconstruct exception received from remote worker.\n"
                    "\n"
                    "Raw remote exception:\n" + pformat(exc)
                ) from e

            # custom_exception.__traceback__ = exc["exception_traceback"] # could cause problems
            # We only make this a warning, because sometimes the client expects an exception and handles it
            # (e.g., when a file does not exist)
            logger.warning(f"[worker] Error on remote worker: {exc['exception_traceback']}")
            raise custom_exception
        elif response.status_code == 401:
            raise AlcatrazAuthError(
                f"You no longer own the VM with machine_info {self.machine_info} there is no hope in retrying this error"
            )
        elif response.status_code != 200:
            raise AlcatrazUnknownError(
                f"Error on remote swarm machine or proxy with status code {response.status_code}: "
                + response.text
                + f"\n\nMachine info:\n\n{self.machine_info}"
            )
        else:
            logger.debug("Unpickling response")
            return msgpack.unpackb(
                base64.b64decode(response.text.encode("utf-8")), object_hook=decode_extras
            )

    async def _heartbeat_once(self) -> bool | None:
        """
        Returns True if the heartbeat was successful, False if the machine is dead,
        and None if transient issues prevented the heartbeat from being sent.
        """
        try:
            response = await _httpx_post(
                self._httpx_client,
                f"http://{self.api_server_host}/im_still_using_machine/",
                params={"scaleset_machineid_ips": self.machine_info},
            )
        except AlcatrazTransientRuntimeError:
            return None
        if response.status_code != 200:
            self._state = _SwarmClusterState.CLOSED
            self._closed_reason = f"because heartbeat http call returned {response.status_code}"
            return False
        self.swarm_metrics["SwarmCluster:max_time_between_heartbeats"] = max(
            self.swarm_metrics.get("SwarmCluster:max_time_between_heartbeats", 0),
            time.time() - self.last_heartbeat_timestamp,
        )
        self.last_heartbeat_timestamp = time.time()
        return True

    async def _heartbeat(self):
        # Under usual circumstances, __aexit__ will tell the api server to kill a machine. But if this doesn't happen for whatever reason, a machine that misses K heartbeats in a row is auto released
        while True:
            logger.info("Thump: Heartbeat is being sent.")
            start_time = time.time()
            res = await self._heartbeat_once()
            logger.info(
                "Heartbeated successfully",
                start_time=start_time,
                end_time=time.time(),
                duration=time.time() - start_time,
                last_heartbeat_timestamp=self.last_heartbeat_timestamp,
                id=repr(self),
                outcome=res,
            )
            # Heartbeat every 5 min; we have a 10 min grace period
            await asyncio.sleep(max(0, _HEARTBEAT_INTERVAL_SECONDS - (time.time() - start_time)))

    async def _save_logs_to_blob_storage(self):
        response = await _httpx_post(
            self._httpx_client,
            f"http://{self.proxy_server_host}/proxy/get_logs",
            json={"machine_info": self.machine_info},
        )
        if response.status_code != 200:
            raise AlcatrazTransientRuntimeError(
                f"Error on remote swarm machine (with status code {response.status_code}) when getting logs: "
                + response.text
            )
        elif response.status_code == 401:
            raise AlcatrazAuthError(
                f"You no longer own the VM with machine_info {self.machine_info} there is no hope in retrying this error"
            )
        else:
            await asyncio.to_thread(
                blob_write,
                f"{self.blob_storage_folder_for_logs}/{self.machine_info}.txt",
                response.text,
            )


# Iterate over superclass methods and create proxies
def _make_proxy_method(method_name: str):
    async def _f(self, *args, **kwargs):
        start_time = time.monotonic()
        try:
            return await self._remote_proxy_method(method_name, *args, **kwargs)
        finally:
            if method_name not in self.swarm_metrics:
                self.swarm_metrics["SwarmCluster:" + method_name] = 0
            self.swarm_metrics["SwarmCluster:" + method_name] += time.monotonic() - start_time

    return _f


for method_name, value in inspect.getmembers(BaseAlcatrazCluster, predicate=inspect.isfunction):
    if method_name.startswith("_") or method_name == "serialize":
        # Skip magic and internal methods along with serializer
        continue
    assert not inspect.isasyncgenfunction(
        value
    ), f"Async generator methods not allowed with swarm cluster. Convert {method_name} to not be a generator (probably return a list?)"
    setattr(SwarmCluster, method_name, _make_proxy_method(method_name))
