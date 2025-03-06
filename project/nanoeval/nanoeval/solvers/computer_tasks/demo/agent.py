import os

import structlog.stdlib

import chz
from nanoeval.setup import nanoeval_entrypoint
from nanoeval.solvers.computer_tasks.demo._demo_task import DemoTask
from nanoeval.solvers.computer_tasks.solver import PythonCodingSolver

logger = structlog.stdlib.get_logger(component=__name__, _print=True)


async def demo(solver: PythonCodingSolver) -> None:
    """
    Demos how to run a basic PythonCodingSolver.
    """

    async with solver:
        async for step in solver.run(task=DemoTask()):
            print("STEP:", step)


if __name__ == "__main__":
    os.environ["NANOEVAL_LOG_ALL"] = "1"
    nanoeval_entrypoint(chz.entrypoint(demo))
