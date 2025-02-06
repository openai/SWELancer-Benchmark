"""
This file defines the data structures used for nanoeval.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Generic, Self, Sequence, TypeVar

from pydantic import BaseModel, field_validator, model_validator

import chz
from nanoeval._multiprocessing_utils import check_multiprocess_safe
from nanoeval.asyncio_utils import HasAsyncContextManager
from nanoeval.json_recorder import json_recorder
from nanoeval.recorder import RecorderConfig


class Task(BaseModel):
    """
    All nanoeval Tasks must inherit from this class.
    """

    # a unique question id for this problem. Equivalent to an "instance" in qstar.
    question_id: str
    # the unique attempt for this question. Equivalent to a "sample" in qstar.
    attempt_id: int = 1
    # the retry index for this attempt. Tasks will be retried until they do not raise a ErrorBlamedOnSystem.
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


@chz.chz
class Eval(Generic[TTask, TResult], HasAsyncContextManager):
    async def get_tasks(self) -> Sequence[TTask]:
        raise NotImplementedError

    async def evaluate(self, task: TTask) -> TResult:
        raise NotImplementedError

    async def get_summary(self, results: list[tuple[TTask, TResult]]) -> dict[str, Any]:
        raise NotImplementedError

    async def update_progress(
        self, partial_results: list[tuple[TTask, TResult]], pbar: Any
    ) -> None:
        """
        Shows intermediate progress. Can update tqdm progress bar.
        """
        del partial_results, pbar
        pass

    def get_name(self) -> str:
        raise NotImplementedError


@chz.chz
class RunnerArgs:
    # Runner options.
    concurrency: int = 4096
    # CURRENTLY EXPERIMENTAL - do not expect any stability!
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
    recorder: RecorderConfig = None
    enable_slackbot: bool = True
    slack_name: str | None = None
    model_name: str | None = None
    eval_set_name: str | None = None
    summary_interval: float | None = None
    use_monitor: bool = chz.field(
        default=False,
        doc="If enabled, starts a streamlit server on port 8501 to monitor the eval. You can also run it manually by running `streamlit run $(oaipkg monorepo)/project/nanoeval/monitor.py`.",
    )
    max_retries: int = chz.field(
        default=16,
        doc="Number of times to retry a task if it raises a RetryableSystemError. Note that no other exception types are retried.",
    )

    # If set, don't run this eval at the same time as other evals. Useful for evals that
    # are sensitive to engine latency, such as agent evals. NOT STABLE and may be
    # removed at any time.
    EXPERIMENTAL_run_isolated: bool = False

    @chz.validate
    def _validate_slackbot_options(self) -> None:
        if self.slack_name and not self.enable_slackbot:
            raise ValueError("slack_name is set but enable_slackbot is False")

    @chz.validate
    def _validate_multiprocessing_options(self) -> None:
        if self.num_processes:
            assert self.num_processes > 0
            assert self.experimental_use_multiprocessing, (
                "num_processes requires experimental_use_multiprocessing"
            )

    @chz.validate
    def _numerical_limits(self) -> None:
        assert self.n_tasks is None or self.n_tasks > 0


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


class RetryableSystemError(Exception):
    """
    An error that is blamed on the system, not the model - hence it should be retried.
    """

    pass
