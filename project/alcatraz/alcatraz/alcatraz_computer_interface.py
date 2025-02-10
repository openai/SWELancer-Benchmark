from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Literal, cast

import async_lru
import structlog.stdlib
from pydantic import BaseModel
from typing_extensions import override

import chz
from alcatraz.clusters.local import BaseAlcatrazCluster, ClusterConfig, LocalConfig
from alcatraz.utils.cmds import run_command_streaming
from nanoeval.solvers.computer_tasks.code_execution_interface import (
    ComputerConfiguration,
    ComputerRuntime,
    ExecutionResult,
    JupyterComputerInterface,
    JupyterExecutionResult,
)
from alcatraz.nanoeval_alcatraz.task_to_alcatraz_config import task_to_alcatraz_config

logger = structlog.stdlib.get_logger(component=__name__)


class Python3ExceptionDict(BaseModel):
    """A pydantic model for serializing a Python 3.x exception.

    Attrs:
        name: The type of the exception, e.g. ValueError.
        traceback: The traceback. Every line ends with a \n.
        args: The args passed to the exception's ctor.
        notes: Future-proofing for PEP 678.
    """

    name: str
    traceback: list[str]
    args: tuple[Any, ...]
    notes: list[str]


class BaseAlcatrazComputerInterface(JupyterComputerInterface, ABC):
    @property
    @abstractmethod
    def cluster(self) -> BaseAlcatrazCluster:
        pass

    async def disable_internet(self) -> None:
        logger.info("Disabling internet on the Swarm VM...")
        await self.cluster.add_weak_network_block_via_ip_tables()

        # Verify
        logger.info("Post-setup network access disabled")
        logger.info("Verified network access successfully disabled")

    async def upload(self, file: bytes, destination: str) -> None:
        return await self.cluster.upload(file, destination)

    async def download(self, file: str) -> bytes:
        return await self.cluster.download(file)

    async def send_shell_command(self, cmd: str) -> ExecutionResult:
        res = await run_command_streaming(self.cluster, cmd)
        return ExecutionResult(output=res["result"], exit_code=res["exit_code"])

    async def fetch_container_names(self) -> list[str]:
        return await self.cluster.fetch_container_names()

    async def stop(self) -> None:
        await self.cluster._stop()

    @override
    async def execute(self, code: str, timeout: int = 120) -> JupyterExecutionResult:
        await self._start_cluster_once()

        messages = await self.cluster.send_kernel_command(code, timeout=timeout)

        # Parse the messages into a final execution result
        # TODO(kevinliu) - this may not be a perfect parsing, but it should only really be used for setup and grade so hopefully it's good enough
        output = ""
        status: Literal["success", "failed_with_in_kernel_exception"] = "success"
        exception = None
        final_expression_output = None
        for msg in messages:
            if msg["msg_type"] == "error":
                # Extract the exception
                exception = Python3ExceptionDict(
                    name=msg["content"]["ename"],
                    traceback=msg["content"]["traceback"],
                    args=(msg["content"]["evalue"],),
                    notes=[],
                )
                status = "failed_with_in_kernel_exception"
            elif msg["msg_type"] == "@timeout":
                status = "failed_with_in_kernel_exception"
            elif msg["msg_type"] == "execute_result":
                final_expression_output = msg["content"]["data"].get("text/plain", "")
            elif msg["msg_type"] == "stream":
                output += msg["content"].get("text", "")

        return JupyterExecutionResult(
            status=status,
            output=output,
            final_expression_output=final_expression_output,
            in_kernel_exception=cast(Any, exception),
            system_exception=None,
        )

    @async_lru.alru_cache(maxsize=1)
    async def _start_cluster_once(self) -> None:
        if not await self.cluster.is_kernel_started():
            await self.cluster.create_kernel_on_machine()


@chz.chz
class AlcatrazComputerInterface(BaseAlcatrazComputerInterface):
    cluster_value: BaseAlcatrazCluster

    @property
    def cluster(self) -> BaseAlcatrazCluster:
        return self.cluster_value


@chz.chz
class AlcatrazComputerRuntime(ComputerRuntime):
    env: ClusterConfig = chz.field(default_factory=LocalConfig)

    @asynccontextmanager
    async def run(
        self, task: ComputerConfiguration
    ) -> AsyncGenerator[AlcatrazComputerInterface, None]:
        async with task_to_alcatraz_config(task, self.env).build() as cluster:
            computer = AlcatrazComputerInterface(cluster_value=cluster)
            yield computer
