"""
This file defines the data structures used for nanoeval.
"""

from __future__ import annotations

import inspect
import logging
import os
from pprint import pformat
from typing import (
    Any,
    Generic,
    Self,
    Sequence,
    TypeVar,
    final,
)

from pydantic import BaseModel, field_validator, model_validator
from tqdm import tqdm

import chz
from chz.factories import function
from nanoeval._multiprocessing_utils import check_multiprocess_safe
from nanoeval.asyncio_utils import HasAsyncContextManager
from nanoeval.recorder_protocol import RecorderConfig


class Task(BaseModel):
    """
    All nanoeval Tasks must inherit from this class.
    """

    question_id: str
    attempt_id: int = 1
    retry_idx: int = 0

    unsafe_skip_serialization_validation: bool = False

    @property
    def name(self) -> str:
        return self.question_id + "." + str(self.attempt_id)

    @field_validator("question_id")
    def no_slash_in_question_id(cls, v: str) -> str:
        if "/" in v:
            raise ValueError('question_id must not contain a "/" character')
        return v

    @model_validator(mode="after")
    def _validate_mp_safe(self) -> Self:
        """
        Tasks must be multiprocessing-safe to be used in nanoeval multiprocessing mode.
        """

        if self.unsafe_skip_serialization_validation:
            return self

        check_multiprocess_safe(self)
        return self

    # subclass this to add more fields


TTask = TypeVar("TTask", bound=Task)
TResult = TypeVar("TResult")


logger = logging.getLogger(__name__)


class RetryableSystemError(Exception):
    """
    An error that is blamed on the system, not the model - hence it should be retried.
    """

    pass


class SystemErrorsNotSupported(ValueError):
    """
    Raised when a summary function does not support system errors.
    """

    pass


def assert_no_system_errors(
    results: Sequence[tuple[TTask, TResult | RetryableSystemError]],
) -> Sequence[tuple[TTask, TResult]]:
    """
    Raises an exception if any of the results are system errors.
    """
    results_clean = [
        (task, result) for task, result in results if not isinstance(result, RetryableSystemError)
    ]
    results_errors = [
        (task, result) for task, result in results if isinstance(result, RetryableSystemError)
    ]
    if len(results_clean) != len(results):
        raise SystemErrorsNotSupported(
            f"Results contain system errors:\n{pformat(results_errors, indent=2)}. This summary function does not handle system errors."
        )

    return results_clean


@chz.chz
class Eval(Generic[TTask, TResult], HasAsyncContextManager):
    def get_name(self) -> str:
        raise NotImplementedError

    async def get_tasks(self) -> Sequence[TTask]:
        raise NotImplementedError

    async def evaluate(self, task: TTask) -> TResult:
        raise NotImplementedError

    async def get_summary(self, results: list[tuple[TTask, TResult]]) -> dict[str, Any]:
        """
        Returns a final summary of evaluation results as a dictionary. Override this class to define metrics (accuracy,
        pass@k, f1, etc.) to compute for a particular eval. It is highly recommended that you use
        `nanoeval.metrics.standard:compute_default_metrics`, as rolling your own metrics can get complicated.

        Note: the results list contains tuples of (task, result). Properties of this list:

        1. len(results) <= len(await self.get_tasks())
        2. Results MAY be ragged, so you should NOT do something like `mean(r.correct for _, r in results)` if your goal
           is to compute accuracy (this will underweight instances with fewer rollouts). Instead, you should compute accuracy
           by instance, and then average over instances.

           Notably, this function is called on an interval, so it should be able to handle partial results and partial
           results are very likely to be ragged.

        This function is called by `eval.get_full_summary()`.
        """
        raise NotImplementedError

    async def get_full_summary(
        self, results: list[tuple[TTask, TResult | RetryableSystemError]]
    ) -> dict[str, Any]:
        """
        Returns a final summary of evaluation results as a dictionary. This is the same as `eval.get_summary()`, but
        it also handles system errors. The default implementation calls `self.get_summary` with system errors that
        are excluded in the top-level metrics, but are marked as failures in the nested `metrics_including_errors` field
        if `eval.process_invalid` is defined.
        """
        from nanoeval.metrics.standard import handle_system_errors_and_compute_metrics

        return await handle_system_errors_and_compute_metrics(
            self.get_summary,
            results,
            process_invalid=self.process_invalid,
        )

    def process_invalid(self, task: TTask) -> TResult:
        """
        Returns the result to use when a system error occurs. This is called when a task raises a RetryableSystemError.
        There is no harm if you don't override this method, but then you don't get summary["metrics_including_errors"].
        """
        raise NotImplementedError

    async def update_progress(
        self, partial_results: list[tuple[TTask, TResult]], pbar: Any
    ) -> None:
        """
        Shows intermediate progress. Can update tqdm progress bar.
        """
        del partial_results, pbar
        pass

    @final
    async def self_test(self) -> None:
        """
        Simple self test to check if the eval is configured correctly. It takes some time to complete, so it is
        recommended that you run this in CI tests to ensure your eval is sane and doesn't have any obvious bugs.
        """
        with tqdm(total=1, desc="Self test") as pbar:
            await self.update_progress([], pbar)

        tasks = await self.get_tasks()
        assert len(tasks) > 0
        assert len(self.get_name()) > 0

        # Basic summary checks
        await self.get_full_summary([])
        # Test robustness to retryable system errors
        try:
            await self.get_full_summary(
                [(task, RetryableSystemError("moo")) for task in tasks[: len(tasks) // 2]]
            )
            await self.get_full_summary([(task, RetryableSystemError("moo")) for task in tasks])
        except SystemErrorsNotSupported:
            # fine if eval explicitly does not support system errors
            pass


@chz.chz
class RunnerArgs:
    # Runner options.
    concurrency: int | None = chz.field(
        default=4096,
        doc="Per-eval concurrency. If None, concurrency is not limited.",
    )
    # If enabled, use multiprocessing. This can be useful for CPU-bound tasks, and uses
    # multiprocessing as the outer loop, and asyncio concurrency as the inner loop.
    # We split tasks into groups of size `concurrency`. A subprocess processes one group
    # at a time, using asyncio inside to parallelize over tasks in the group. If enabled,
    # you will probably want lower concurrency as well, such that each subprocess is not CPU-bound.
    experimental_use_multiprocessing: bool = False
    num_processes: int | None = chz.field(
        default=None,
        doc="If set, use this many executor processes to run the eval. Note that because nanoeval uses a shared process pool for all evals, the first eval run will determine the number of processes for all evals.",
    )
    shuffle: bool = False
    n_tasks: int | None = chz.field(
        default=None,
        doc="Limit the number of tasks run. The limit is the first N tasks selected before shuffling.",
    )
    run_set_id: str | None = None
    recorder: RecorderConfig | None = chz.field(
        meta_factory=function(),
        default=None,
        doc="Recorder configuration used to create a recorder for the eval. If None, default recorder is used (as determined by `library_config().get_default_recorder()`.",
    )
    enable_slackbot: bool = True
    slack_name: str | None = None
    model_name: str | None = None
    eval_set_name: str | None = None
    summary_interval: float | None = None
    use_monitor: bool = chz.field(
        default=False,
        doc="If enabled, starts a streamlit server on port 8501 to monitor the eval. You can also run it manually by running `python3 -m nanoeval.bin.mon`.",
    )
    max_retries: int = chz.field(
        default=16,
        doc="Number of times to retry a task if it raises a RetryableSystemError. Note that no other exception types are retried.",
    )
    should_backup: bool = chz.field(
        default=True,
        doc="If enabled, backup the run state database to Azure Blob Storage.",
    )

    @chz.validate
    def _validate_slackbot_options(self) -> None:
        if self.slack_name and not self.enable_slackbot:
            raise ValueError("slack_name is set but enable_slackbot is False")

    @chz.validate
    def _validate_multiprocessing_options(self) -> None:
        if self.num_processes:
            assert self.num_processes > 0
            assert (
                self.experimental_use_multiprocessing
            ), "num_processes requires experimental_use_multiprocessing"

    @chz.validate
    def _numerical_limits(self) -> None:
        assert self.n_tasks is None or self.n_tasks > 0

    @chz.validate
    def _validate_concurrency(self) -> None:
        if self.concurrency is not None and self.concurrency <= 0:
            if self.concurrency == 0 and os.environ.get("NANOEVAL_ALLOW_ZERO_CONCURRENCY"):
                pass
            else:
                raise ValueError(
                    "concurrency must be > 0 or None unless NANOEVAL_ALLOW_ZERO_CONCURRENCY is set."
                )


@chz.chz
class EvalSpec:
    """
    Configuration for running a single eval using nanoeval. Represents the
    eval and how to run it.
    """

    # The eval to run
    eval: Eval[Any, Any]
    runner: RunnerArgs

    @chz.validate
    def _pickleable_in_mp_mode(self) -> None:
        """
        We assert that the eval can be pickled. This is because
        we have to send it to the subprocesses OR in-process executor via pickle.

        (Note we actually use dill, a slightly more powerful pickle, but it's not magic.)
        """

        check_multiprocess_safe(self)
        assert self.eval.__module__ != "__main__", (
            f"The eval class {self.eval.__module__}:{self.eval.__class__.__name__} must not be defined in the __main__ module.\n\n"
            "This is because the __main__ module is treated specially by dill (used internally to serialize state in nanoeval) and "
            "is serialized by value rather than by reference. This breaks serialization in subtle ways and is usually not what you "
            f"want. To fix this, move the eval class from {inspect.getfile(self.eval.__class__)} to a different module.\n\n"
            "References:\n"
            "- https://oegedijk.github.io/blog/pickle/dill/python/2020/11/10/serializing-dill-references.html\n"
            "- https://stackoverflow.com/questions/73584583/importerror-for-top-level-package-when-trying-to-use-dill-to-pickle-entire-packa"
        )

    async def model_name(self) -> str:
        if self.runner.model_name:
            return self.runner.model_name
        else:
            logger.warning("Unable to find model name, using fallback name='nanoeval'")
            return "nanoeval"
