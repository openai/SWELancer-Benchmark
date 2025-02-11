from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

import nanoeval
from nanoeval.eval import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.json_recorder import JsonRecorderConfig
from nanoeval.setup import global_exit_stack
from nanoeval.solvers.mcq import MockSolver


@pytest.mark.asyncio
async def test_json_recorder_works() -> None:
    async with global_exit_stack:
        with NamedTemporaryFile() as tmpfile:
            await nanoeval.run(
                EvalSpec(
                    eval=GPQAEval(solver=MockSolver()),
                    runner=RunnerArgs(
                        n_tasks=1, recorder=JsonRecorderConfig(filename=Path(tmpfile.name))
                    ),
                )
            )

            assert len(Path(tmpfile.name).read_text().split("\n")) == 5
