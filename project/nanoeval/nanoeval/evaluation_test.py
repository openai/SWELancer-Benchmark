from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
import pytest
from typing_extensions import override

import chz
import nanoeval
import nanoeval._db as db
from nanoeval.asyncio_utils import cancel_task
from nanoeval.evaluation import EvalSpec, RetryableSystemError, RunnerArgs, Task
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.setup import global_exit_stack
from nanoeval.solvers.mcq import Answer, MCQSolver, MCQTask, MockSolver


@pytest.mark.asyncio
async def test_concurrency_blocking_edge_case() -> None:
    """
    If one eval is waiting on concurrency limit, we should not let that block the other eval.

    If this test fails, it will hang forever.
    """
    async with global_exit_stack, db.open_run_set_db(backup=False), asyncio.TaskGroup() as tg:
        # This eval will never finish and get queued in the executor forever.
        # Note concurrency=0.
        background = tg.create_task(
            nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=MockSolver()),
                    runner=RunnerArgs(n_tasks=1, concurrency=0),
                )
            )
        )

        # Wait for the task to get registered
        while True:
            with db.conn() as c:
                (count,) = c.execute("SELECT COUNT(*) FROM eval").fetchone()
                if count > 0:
                    break
            await asyncio.sleep(0.5)

        print("made it to the point where the first one got picked up by the executor")

        for f in asyncio.as_completed(
            [
                # Will never finish - and that's ok!
                background,
                # We expect this one to actually finish.
                nanoeval.validate(
                    EvalSpec(
                        eval=GPQAEval(solver=MockSolver()),
                        runner=RunnerArgs(n_tasks=1, concurrency=1),
                    )
                ),
            ]
        ):
            await f
            print("We did it! one of the evals finished!")
            await cancel_task(background)
            break


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_cls",
    [GeneratorExit, KeyboardInterrupt, RuntimeError],
)
async def test_evals_raising_weird_errors(error_cls: type[BaseException]) -> None:
    """
    Previously we didn't properly handle exceptions that are not subclasses of Exception.

    This test serves as a regression check to assert that the evaluation system raises an
    error when any weird exception is raised during evaluation.
    """

    @chz.chz
    class SadMCQSolver(MCQSolver[Answer]):
        @override
        async def solve(self, task: MCQTask) -> Answer:
            raise error_cls()

    with pytest.raises(ExceptionGroup):
        async with global_exit_stack:
            # note: fn will hang if the error is not caught. this should be considered a failure.
            await nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=SadMCQSolver()),
                    runner=RunnerArgs(n_tasks=1),
                )
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("use_multiprocessing", [True, False])
async def test_does_not_start_multiple_executors(use_multiprocessing: bool) -> None:
    """
    Regression test. Previously, the evaluation system would start the executors
    multiple times when running multiple evaluations in the same process.
    """

    def num_executors() -> int:
        with db.conn() as c:
            return c.execute("SELECT COUNT(*) FROM executor").fetchone()[0]

    num_desired_executors = 1

    kwargs = {"n_tasks": 1, "experimental_use_multiprocessing": use_multiprocessing}
    if use_multiprocessing:
        kwargs |= {"num_processes": num_desired_executors}
    args = RunnerArgs(**kwargs)

    async with global_exit_stack:
        await nanoeval.validate(EvalSpec(eval=GPQAEval(solver=MockSolver()), runner=args))
        assert num_executors() == num_desired_executors

        # The second evaluation should not start a new executor.
        await nanoeval.validate(EvalSpec(eval=GPQAEval(solver=MockSolver()), runner=args))
        assert num_executors() == num_desired_executors


@pytest.mark.asyncio
async def test_retryable_system_errors() -> None:
    @chz.chz
    class SadMCQSolver(MCQSolver[Answer]):
        """
        An MCQ solver that fails once and then succeeds for every new instance.
        """

        seen_tasks: set[str] = chz.field(default_factory=set)

        @override
        async def solve(self, task: MCQTask) -> Answer:
            if task.question_id not in self.seen_tasks:
                self.seen_tasks.add(task.question_id)
                raise RetryableSystemError("failing once for test purposes")

            return Answer(correct=True, picked=task.question.correct_indices.pop())

    async with global_exit_stack:
        report = await nanoeval.validate(
            EvalSpec(
                eval=GPQAEval(solver=SadMCQSolver()),
                runner=RunnerArgs(n_tasks=1),
            )
        )
        assert np.isclose(report["accuracy"], 1.0)


@pytest.mark.asyncio
async def test_errors_in_summary() -> None:
    max_retries = 2
    sentinel_made_it_here = 0.1337

    @chz.chz
    class SadEval(nanoeval.Eval[Task, Any]):
        @override
        def get_name(self) -> str:
            return "SadEval"

        @override
        async def get_tasks(self) -> list[Task]:
            return [Task(question_id="x")]

        @override
        async def evaluate(self, task: Task) -> Any:
            del task
            raise RetryableSystemError("failing for test purposes")

        @override
        async def get_full_summary(
            self, results: list[tuple[Task, RetryableSystemError]]
        ) -> dict[str, Any]:
            # Override full summary so we can observe system errors
            assert len(results) == 1
            # should have retried many times!!
            assert results[0][0].retry_idx == max_retries
            assert isinstance(results[0][1], RetryableSystemError)
            return {"accuracy": sentinel_made_it_here}

    async with global_exit_stack:
        report = await nanoeval.validate(
            EvalSpec(
                eval=SadEval(),
                runner=RunnerArgs(n_tasks=1, max_retries=max_retries),
            )
        )
        assert report["accuracy"] == sentinel_made_it_here


@pytest.mark.asyncio
@pytest.mark.parametrize("use_multiprocessing", [True, False])
@pytest.mark.parametrize("n_evals", [1, 2])
async def test_run_gpqa(use_multiprocessing: bool, n_evals: int) -> None:
    async with global_exit_stack:
        # smoke test for data loading, validation, solving in several configurations
        for _ in range(n_evals):
            report = await nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=MockSolver()),
                    runner=RunnerArgs(
                        experimental_use_multiprocessing=use_multiprocessing,
                    ),
                )
            )
            assert "accuracy" in report


@pytest.mark.asyncio
async def test_concurrency_limits() -> None:
    @chz.chz
    class ConcurrencyAwareSolver(MCQSolver[Answer]):
        """
        An MCQ solver that records the number of concurrent instances.
        """

        concurrent_instances: int = chz.field(default=0)
        max_concurrent_instances: int = chz.field(default=0)

        @override
        async def solve(self, task: MCQTask) -> Answer:
            object.__setattr__(self, "concurrent_instances", self.concurrent_instances + 1)
            object.__setattr__(
                self,
                "max_concurrent_instances",
                max(self.max_concurrent_instances, self.concurrent_instances),
            )
            await asyncio.sleep(0.1)  # Simulate some processing time
            object.__setattr__(self, "concurrent_instances", self.concurrent_instances - 1)
            if self.max_concurrent_instances > 4:
                raise RuntimeError("Too many concurrent instances")
            return Answer(correct=True, picked=task.question.correct_indices.pop())

    solver = ConcurrencyAwareSolver()

    async with global_exit_stack:
        # ok
        report = await nanoeval.validate(
            EvalSpec(
                eval=GPQAEval(solver=solver),
                runner=RunnerArgs(concurrency=4),
            )
        )
        assert "accuracy" in report

    # not ok
    with pytest.raises(ExceptionGroup):
        async with global_exit_stack:
            await nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=solver),
                    runner=RunnerArgs(concurrency=5),
                )
            )


@pytest.mark.asyncio
async def test_crashes_passed_through_multiprocessing() -> None:
    @chz.chz
    class CrashingSolver(MCQSolver[Answer]):
        """
        An MCQ solver that crashes intentionally.
        """

        @override
        async def solve(self, task: MCQTask) -> Answer:
            del task
            raise RuntimeError("Intentional crash for testing purposes")

    crashing_solver = CrashingSolver()

    with pytest.raises(ExceptionGroup):
        async with global_exit_stack:
            await nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=crashing_solver),
                    runner=RunnerArgs(
                        concurrency=1, experimental_use_multiprocessing=True, num_processes=1
                    ),
                )
            )


@pytest.mark.asyncio
async def test_tasks_crash_in_second_eval() -> None:
    """
    Regression test. Previous bug:

    1. nanoeval thinks that as long as an executor is alive, life is good, and it won't reassign the task away
    2. executors basically label tasks from sqlite as "mine," insert them into an internal queue, and process them in order
    3. if one of the 1st tasks crashes the executor, the internal queue is lost. usually this is fine because this
       raises an exception in the driver which causes the driver+worker to crash, but if this doesn't happen then the worker
       will be a zombie and the pid stays around.

       The driver might not crash if two evals are run, which would previously trigger *too many* executor tasks to be
       assigned to the executor pool. The first set of exception listeners would all terminate with the first successful
       eval, but the second eval would reuse the executors from the first evals now with *no exception listeners*!
    4. if the pid stays around, you get "zombie" tasks that are associated with an executor but not actually queued up
       to run anywhere! a terrible bug.

    NOTE: If regression test fails, it will hang forever rather than crashing.
    """

    @chz.chz
    class CrashingSolver(MCQSolver[Answer]):
        """
        An MCQ solver that crashes intentionally.
        """

        @override
        async def solve(self, task: MCQTask) -> Answer:
            del task
            raise RuntimeError("Intentional crash for testing purposes")

    first_eval_succeeded = False

    # The exception group actually gets raised at global_exit_stack

    with pytest.raises(ExceptionGroup):  # noqa: PT012
        async with global_exit_stack:
            # First run a normal eval, no problem here.
            await nanoeval.validate(
                EvalSpec(
                    eval=GPQAEval(solver=MockSolver()),
                    runner=RunnerArgs(
                        n_tasks=1, num_processes=1, experimental_use_multiprocessing=True
                    ),
                )
            )

            first_eval_succeeded = True

            # The second one must crash.
            with pytest.raises(ExceptionGroup):
                await nanoeval.validate(
                    EvalSpec(
                        eval=GPQAEval(solver=CrashingSolver()),
                        runner=RunnerArgs(
                            n_tasks=1, num_processes=1, experimental_use_multiprocessing=True
                        ),
                    )
                )

    assert first_eval_succeeded
