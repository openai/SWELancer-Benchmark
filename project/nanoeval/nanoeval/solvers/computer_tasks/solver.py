from __future__ import annotations

import asyncio
import itertools
import os
import time
from abc import ABC, abstractmethod
from asyncio import CancelledError
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Sequence

import numpy as np
import structlog.stdlib
from pydantic import BaseModel
from typing_extensions import override

import chz
import nanoeval
from nanoeval.asyncio_utils import HasAsyncContextManager, generator_with_cleanup
from nanoeval.eval import RetryableSystemError
from nanoeval.metrics.agents import get_summary_error_aware
from nanoeval.recorder import RecorderProtocol, get_recorder
from nanoeval.solvers.computer_tasks.steps import (
    FinalResult,
    FinalResultSuccessful,
    FinalResultWithException,
    Step,
)
from nanoeval.solvers.computer_tasks.task import ComputerTask, Grade

logger = structlog.stdlib.get_logger(component=__name__)


@chz.chz
class PythonCodingSolver(ABC, HasAsyncContextManager):
    """
    A solver for tasks that run on a container.
    """

    @abstractmethod
    def shortname(self) -> str:
        pass

    @abstractmethod
    def run(self, task: ComputerTask) -> AsyncGenerator[Step | FinalResult, None]:
        """
        Runs the solver on the given task.
        """
        pass


@chz.chz
class DummyPythonCodingSolver(PythonCodingSolver):
    """
    A dummy solver that always returns correct. NOTE that this doesn't exercise
    environment setup - for that, something like the ACE gold solver (to be written)
    should be used.
    """

    @override
    def shortname(self) -> str:
        return "dummy"

    @override
    async def run(self, task: ComputerTask) -> AsyncGenerator[Step | FinalResult, None]:
        del task
        yield FinalResultSuccessful(
            grade=Grade(score=1, grader_log="Dummy solver always returns correct")
        )


def strip_all_metadata(
    convo: BaseModel, allowed_metadata_fields: list[str] | None = None
) -> BaseModel:
    """
    Strip all metadata from a conversation. We can't use evallib's remove_all_metadata
    function because it recently introduced a change that enforces metadata is
    serializable, but evidently some UUIDs end up in metadata eventually.
    """
    # Delete all the metadata from the conversation and messages.
    if allowed_metadata_fields is None:
        allowed_metadata_fields = []
    convo = convo.model_copy(
        update={
            "metadata": {k: v for k, v in convo.metadata.items() if k in allowed_metadata_fields}  # type: ignore
        }
    )
    for msg in convo.messages:  # type: ignore
        msg.metadata = {k: v for k, v in msg.metadata.items() if k in allowed_metadata_fields}
    return convo


@contextmanager
def simple_timer(name: str) -> Generator[None, None, None]:
    logger.info(f"[{name}] started")
    start = time.monotonic()
    try:
        yield
        logger.info(f"[{name}] finished", elapsed=time.monotonic() - start)
    except Exception:
        logger.warning(f"[{name}] failed", elapsed=time.monotonic() - start)
        raise


logged_messages = set()


def _log(
    recorder: RecorderProtocol,
    step: Step | FinalResult,
    record_pretty: bool = False,  # records each message as a pretty-printed sampling. may cut off certain messages or information.
) -> None:
    """
    Log a data point to the recorder.
    """
    assert recorder is not None

    if not record_pretty:
        # Clean all metadata to make the recording shorter.
        if step.convo:
            # TODO(kevinliu) restore these
            step.convo = strip_all_metadata(step.convo)

        # For intermediate steps, only log the last 5 messages of the convo to save space.
        # The final result will always have the full conversation.
        if isinstance(step, Step):
            step.convo = step.convo.model_copy()
            step.convo.messages = step.convo.messages[-5:]

        try:
            recorder.record_extra(data=step.model_dump(mode="json"))
        except Exception:
            logger.warning("Failed to record extra data", exc_info=True)
    else:
        # Log all messages, but skip ones we've already recorded
        if step.convo is not None:
            for message in step.convo.messages[-15:]:
                if message.id in logged_messages:
                    continue
                else:
                    logged_messages.add(message.id)

                try:
                    record_message(recorder, message)
                except Exception as e:
                    logger.warning("Failed to record message", error=e)


def record_message(recorder: RecorderProtocol, message: Any) -> None:
    # TODO(kevinliu/extract) fix logging here
    text = str(message)
    author = str(message.author.role)
    status = (str(message.status),)
    end_turn = (message.end_turn,)
    recipient = message.recipient

    prompt = f"""
    Author: {author}
    Status: {status}
    End Turn: {end_turn}
    Recipient: {recipient}
    """
    sampled = text

    recorder.record_sampling(
        prompt=prompt,
        sampled=sampled,
    )


def _log_results(task: ComputerTask, result: FinalResult) -> None:
    """
    Log the results of a task.
    """
    recorder = get_recorder()

    score = result.grade.score
    log = result.grade.grader_log

    recorder.record_sampling(
        prompt="",
        sampled=log,
        sample_id=task.question_id,
        group_id=str(task.attempt_id),
    )

    recorder.record_match(
        correct=bool(score),
        group_id=str(task.attempt_id),
    )


@chz.chz
class PythonCodingEval(nanoeval.Eval[ComputerTask, FinalResult]):
    solver: PythonCodingSolver = DummyPythonCodingSolver()
    n_tries: int = 1
    record_pretty: bool = False
    log_at_end: bool = False

    @override
    @asynccontextmanager
    async def _context(self) -> AsyncGenerator[None, None]:
        async with self.solver:
            yield

    @abstractmethod
    async def get_instances(self) -> Sequence[ComputerTask]:
        pass

    @override
    async def get_tasks(self) -> Sequence[ComputerTask]:
        questions = await self.get_instances()

        tasks = []
        for attempt_idx, (_q_idx, question) in itertools.product(
            range(self.n_tries), enumerate(questions)
        ):
            tasks.append(
                question.model_copy(
                    update=dict(attempt_id=attempt_idx, question_id=question.question_id)
                )
            )

        return tasks

    async def _evaluate_inner(self, task: ComputerTask) -> FinalResult:
        recorder = get_recorder()
        try:
            async with generator_with_cleanup(self.solver.run(task)) as gen:
                async for step in gen:
                    assert not isinstance(step, FinalResultWithException), (
                        "FinalResultWithException has been deprecated"
                    )

                    await asyncio.to_thread(
                        _log,
                        recorder,
                        step,
                        self.record_pretty,
                    )
                    if isinstance(step, FinalResultSuccessful):
                        logger.info(
                            "Final result: %s (%d messages)",
                            step.correct,
                            len(step.convo.messages) if step.convo else 0,
                        )

                        # For compatibility with simple evalboard vis, log a match.
                        await asyncio.to_thread(recorder.record_match, correct=step.correct)
                        return step
        except CancelledError as e:
            logger.exception("Cancelled error detected - this is clearly a bug")
            raise RetryableSystemError("Cancelled error detected - this is clearly a bug") from e
        raise ValueError("Solver did not return a final result! This is a programming error.")

    @override
    async def evaluate(self, task: ComputerTask) -> FinalResult:
        # print machine statistics, useful for debugging in a multiprocess setting
        logger.info("PID: %d", os.getpid())
        logger.info("To dump stack traces: $ py-spy dump --pid %d", os.getpid())
        logger.info("PythonCodingEval.evaluate() started")
        res = await self._evaluate_inner(task)
        if self.log_at_end:
            logger.info("PythonCodingEval.evaluate() logging")
            await asyncio.to_thread(_log_results, task, res)
        logger.info("PythonCodingEval.evaluate() finished")
        return res

    def process_invalid(self, task: ComputerTask) -> FinalResult:
        return FinalResultSuccessful(grade=Grade(score=0, grader_log="Task was invalid"))

    @override
    async def update_progress(
        self,
        partial_results: list[
            tuple[ComputerTask, FinalResultSuccessful | FinalResultWithException]
        ],
        pbar: Any,
    ) -> None:
        summary: dict[str, Any] = {
            "num_correct": 0,
            "num_incorrect": 0,
            "num_incorrect_with_error": 0,
            "num_incorrect_max_steps_reached": 0,
            "error_breakdown": defaultdict(int),
        }

        for _task, result in partial_results:
            if result.correct:
                summary["num_correct"] += 1
            else:
                summary["num_incorrect"] += 1

            if isinstance(result, FinalResultWithException):
                summary["error_breakdown"][result.exception] += 1
                summary["num_incorrect_with_error"] += 1
            elif result.max_steps_reached:
                summary["num_incorrect_max_steps_reached"] += 1

        pbar.set_postfix(
            corr=summary["num_correct"],
            errs=summary["num_incorrect_with_error"],
            fail=summary["num_incorrect"] - summary["num_incorrect_with_error"],
        )

    def _get_convo_len_stats(
        self, results: list[tuple[ComputerTask, FinalResult | RetryableSystemError]]
    ) -> dict[str, Any]:
        """
        Get conversation length statistics.
        """
        completions = [result for _, result in results if isinstance(result, FinalResultSuccessful)]
        if not completions:
            return {}
        frac_correct = sum(1 for result in completions if result.correct) / len(completions)
        incorrect_completions = [result for result in completions if not result.correct]
        frac_max_time = sum(1 for result in incorrect_completions if result.max_time_reached) / len(
            completions
        )
        frac_max_steps = sum(
            1 for result in incorrect_completions if result.max_steps_reached
        ) / len(completions)
        frac_max_tokens = sum(
            1 for result in incorrect_completions if result.max_tokens_reached
        ) / len(completions)
        frac_model_ended = sum(
            1
            for result in incorrect_completions
            if not (
                result.max_time_reached or result.max_steps_reached or result.max_tokens_reached
            )
        ) / len(completions)
        convos = [result.convo for result in completions if result.convo is not None]

        summary_dict = {
            "frac_correct": frac_correct,
            "frac_max_time": frac_max_time,
            "frac_max_steps": frac_max_steps,
            "frac_max_tokens": frac_max_tokens,
            "frac_model_ended": frac_model_ended,
        }

        if not convos:
            return summary_dict

        convo_lens = [len(convo.messages) for convo in convos]
        # compute percentiles
        convo_lens = np.array(convo_lens)
        percentiles = np.percentile(convo_lens, [25, 50, 75])
        summary_dict["convo_len_percentiles"] = percentiles.tolist() # type: ignore

        return {
            "frac_correct": frac_correct,
            "frac_max_time": frac_max_time,
            "frac_max_steps": frac_max_steps,
            "frac_max_tokens": frac_max_tokens,
            "frac_model_ended": frac_model_ended,
            "convo_len_percentiles": percentiles.tolist(),
        }

    @override
    async def get_full_summary(
        self, results: list[tuple[ComputerTask, FinalResult | RetryableSystemError]]
    ) -> dict[str, Any]:
        """
        How are results classified?

        - FinalResultSuccessful -> goes in correct/incorrect
        - FinalResultWithException -> shouldn't exist anymore
        - RetryableSystemError -> marked as has_error, ignored in default metrics, but counted in metrics_including_errors
        """

        for _, result in results:
            assert not isinstance(result, FinalResultWithException), (
                "FinalResultWithException has been deprecated in favor of nanoeval system retries"
            )

        summary = await asyncio.to_thread(
            get_summary_error_aware,
            [
                (
                    task,
                    (
                        result.correct
                        if isinstance(result, (FinalResultSuccessful, FinalResultWithException))
                        else result
                    ),
                )
                for task, result in results
            ],
        )
        summary["length_stats"] = self._get_convo_len_stats(results)

        return summary
