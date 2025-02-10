import ast
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any, AsyncContextManager, Literal, Sequence

from IPython.core.inputtransformer2 import TransformerManager
from pydantic import BaseModel, field_validator
from typing_extensions import deprecated

import chz


class JupyterExecutionResult(BaseModel):
    status: Literal[
        "running",
        "success",
        "cancelled",
        "failed_with_in_kernel_exception",
        "failed_with_system_exception",
        "failed_with_kernel_death",
        "failed_with_response_too_large",
    ]
    output: str
    final_expression_output: str | None
    in_kernel_exception: Any | None = None
    system_exception: Any | None = None

    @cached_property
    def parsed_final_expression_output(self) -> Any:
        if not self.final_expression_output:
            return None
        return ast.literal_eval(self.final_expression_output)


class ExecutionResult(BaseModel):
    output: bytes
    exit_code: int


class ComputerInterface(ABC):
    """
    Represents a rollout's connection to a computer. This represents the "runtime state"
    of a Task, and is an abstraction that lets you write assertions and tests against a computer without regard to the
    backend.

    Note that a ComputerInterface does not "own" the underlying resource, as in when a ComputerInterface for a cluster
    resource gets deleted, the cluster itself does not necessarily stop. It is the responsibility of the code that
    created the underlying resource to manage its lifecycle and dispose of it.
    """

    @abstractmethod
    async def disable_internet(self) -> None:
        """
        Disables outbound internet access for the container. Any other containers on the local network
        should still be accessible.
        """
        pass

    @abstractmethod
    async def upload(self, file: bytes, destination: str) -> None:
        pass

    @abstractmethod
    async def download(self, file: str) -> bytes:
        pass

    @abstractmethod
    async def send_shell_command(self, cmd: str) -> ExecutionResult:
        """
        Executes the shell command in a new bash shell. Every command should be unique
        in terms of environment, etc.
        """

    async def check_shell_command(self, cmd: str) -> ExecutionResult:
        res = await self.send_shell_command(cmd)
        assert res.exit_code == 0, (
            f"Command failed with {res.exit_code=}\n\n{res.output.decode(errors='ignore')}"
        )
        return res

    @abstractmethod
    @deprecated("Only CTFs should use this function")
    async def fetch_container_names(self) -> list[str]:
        """
        TODO(kevinliu): This function really shouldn't need to be here; it's a layering
        violation. We should not require eval tasks to manage individual containers in code.

        Remove once CTFs no longer use this in their prompts.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        # Stops the computer. If used, the computer will no longer be accessible after this and the behavior
        # of all other functions is undefined.
        pass


class JupyterComputerInterface(ComputerInterface):
    """
    A computer upon which a jupyter kernel has been started. It can accept commands.
    """

    @abstractmethod
    async def execute(self, code: str, timeout: int = 120) -> JupyterExecutionResult:
        """
        Execute the given Python code and return the result.
        """
        pass

    async def check_execute(self, code: str) -> JupyterExecutionResult:
        """
        Execute the given Python code and return the result.
        """
        res = await self.execute(code)
        assert res.status == "success", (res, code)
        return res


# TODO(kevinliu) gpus?
class ContainerResources(BaseModel):
    """
    Resources requested for a container. The defaults are set pretty low to encourage conservation
    and make downstream evals more explicit about their resource requirements.
    """

    # number of cpus (default)
    cpu: float = 0.2
    # amount of memory in MB
    memory: int = 1024


class ComputerConfiguration(BaseModel):
    """
    Very roughly, this class represents how to construct a Docker Compose-style workload for a
    model rollout. It is written mostly generically, such that people can write their own
    `ComputerRuntime` that provides a `ComputerInterface` for downstream code and solvers.
    """

    # cwd: the working directory for the task. Typically, a solver can use this
    # to cd into the directory where the data for the task is located.
    cwd: str = "/root"

    # Custom docker image to start execution in. Must have Python installed.
    # If not specified, depends on the execution environment - so I highly recommend
    # specifying the image if your task has any dependencies at all.
    docker_image: str | None = None

    # Side containers to run alongside the main container.
    side_images: list[str] = []
    docker_compose_yaml: str | None = None

    # Resource requirements for the main container.
    # See SwarmCluster for a definition.
    azure_vm_sku: str | None = None
    disk_mount_path: str | None = None

    azure_files_config: dict[str, str] | None = None
    azure_container_config: dict[str, str] | None = None
    volumes_config: dict[str, Any] = {}
    shm_size: str | None = None
    # TODO(kevinliu) remove this
    mem_limit: str | None = None
    timeout: int | None = None
    alcatraz_limits: dict[str, Any] | None = None

    # Code to run the jupyter kernel in conda
    jupyter_setup: Sequence[str] | None = None

    # Allow setting custom environment variables
    environment: dict[str, Any] = {}

    resources: ContainerResources = ContainerResources()
    limits: ContainerResources = ContainerResources()
    allow_internet: bool = False

    # Validators
    @field_validator("cwd")
    @classmethod
    def _validate_cwd(cls, v: str) -> str:
        assert Path(v).is_absolute(), "cwd must be an absolute path."
        return v


@chz.chz
class ComputerRuntime(ABC):
    """
    Represents a runtime to run a ComputerTask. You can use this class to build simple portable Solvers that
    are environment-agnostic.

    Many realistic solvers may be implementation-specific and will not use this interface directly, but may use
    a concrete downstream implementation.

    """

    @abstractmethod
    def run(self, task: ComputerConfiguration) -> AsyncContextManager[ComputerInterface]:
        """
        Start the task. Returns a context manager that owns the underlying container and will stop the underlying
        resources when the context manager exits.
        """
        pass


def valid_ipython_code(code: str) -> bool:
    # Parse the code using ast to check for syntax errors.
    # NOTE: technically, might be unsound if the ACE environment
    # has a newer Python than the one we're using here. But atm
    # (4/3/24), this is not the case.
    tm = TransformerManager()  # type: ignore
    transformed_code = tm.transform_cell(code)
    try:
        ast.parse(transformed_code)
        return True
    except SyntaxError:
        return False
    except Exception as e:
        raise ValueError("Error parsing code") from e
