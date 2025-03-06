import os

import structlog.stdlib

import chz
from nanoeval.async_breakpoint import abreakpoint
from nanoeval.setup import nanoeval_entrypoint
from nanoeval.solvers.computer_tasks.code_execution_interface import (
    ComputerConfiguration,
    ComputerRuntime,
    JupyterComputerInterface,
)

logger = structlog.stdlib.get_logger(component=__name__, _print=True)


async def demo(runtime: ComputerRuntime) -> None:
    """
    Demos how the ComputerTask data structures work together to define a rollout.

    Example (using Alcatraz):

    $ python3 -m nanoeval.solvers.computer_tasks.demo runtime=nanoeval_alcatraz.alcatraz_computer_interface:AlcatrazComputerRuntime
    """

    demo_task = ComputerConfiguration()
    async with runtime.run(demo_task) as computer:
        logger.info(str(await computer.check_shell_command("echo hello from the other side")))
        if isinstance(computer, JupyterComputerInterface):
            logger.info(str(await computer.execute("print('moo')")))
            logger.info(str(await computer.execute("raise RuntimeError")))

        # Enter an interactive console
        await abreakpoint()


if __name__ == "__main__":
    os.environ["NANOEVAL_LOG_ALL"] = "1"
    nanoeval_entrypoint(chz.entrypoint(demo))
