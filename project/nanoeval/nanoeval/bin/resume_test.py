from tempfile import NamedTemporaryFile

import pytest
from typing_extensions import override

import chz
import nanoeval
from nanoeval._db import conn, open_run_set_db
from nanoeval.bin.resume import resume
from nanoeval.eval import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.setup import global_exit_stack
from nanoeval.solvers.mcq import Answer, MCQSolver, MCQTask


@chz.chz
class ConfigurableCrashingSolver(MCQSolver[Answer]):
    name: str

    @override
    async def solve(self, task: MCQTask) -> Answer:
        del task
        if open(self.name).read() == "True":
            raise RuntimeError("Intentional crash for testing purposes")
        return Answer(correct=True, picked=0)


@pytest.mark.asyncio
async def test_gpqa_eval_resumption() -> None:
    """
    We test resumption by:

    - Forcing an exit via a global variable
    - Running the eval until it crashes
    - Resuming it from the database
    - Checking that the eval finishes successfully!
    """

    with NamedTemporaryFile("w") as f:
        # We use a tempfile to store whether or not to crash
        # we have to do this because multiprocessing doesn't share global vars
        f.write("True")
        f.flush()

        crashing_solver = ConfigurableCrashingSolver(name=f.name)

        async with open_run_set_db(backup=True):
            with conn() as c:
                run_set_id = c.execute(
                    "select value from metadata where key='run_set_id'"
                ).fetchone()[0]

            # This should crash
            with pytest.raises(ExceptionGroup) as exc:
                async with global_exit_stack:
                    await nanoeval.validate(
                        EvalSpec(
                            eval=GPQAEval(solver=crashing_solver),
                            runner=RunnerArgs(
                                concurrency=1,
                                experimental_use_multiprocessing=True,
                                num_processes=1,
                                n_tasks=12,
                            ),
                        )
                    )

            print(exc)

        print("MADE IT HERE")
        # Disable the crash
        with open(f.name, "w") as f2:
            f2.write("False")

        async with global_exit_stack:
            # Resume the eval
            [summary] = await resume(run_set_id=run_set_id)
            assert summary["accuracy"] == 1.0
