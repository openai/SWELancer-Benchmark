from __future__ import annotations

import functools
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Literal, Self

import pandas as pd
import structlog

import chz
from nanoeval.recorder_protocol import BasicRunSpec, RecorderConfig, RecorderProtocol

if TYPE_CHECKING:
    from nanoeval.eval import EvalSpec


@functools.cache
def root_dir() -> Path:
    return Path(tempfile.gettempdir()) / "nanoeval"


logger = structlog.stdlib.get_logger(component=__name__)


@dataclass
class _DefaultDummyRecorder(RecorderProtocol):
    run_spec: BasicRunSpec  # type: ignore

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def current_sample_id(self) -> str | None:
        return None

    def current_group_id(self) -> str | None:
        return None

    def record_match(
        self,
        correct: bool,
        *,
        expected: Any = None,
        picked: Any = None,
        prob_correct: Any = None,
        **extra: Any,
    ) -> None:
        pass

    @contextmanager
    def as_default_recorder(
        self, sample_id: str, group_id: str, **extra: Any
    ) -> Generator[None, None, None]:
        yield

    def record_sampling(
        self,
        prompt: Any,
        sampled: Any,
        *,
        extra_allowed_metadata_fields: list[str] | None = None,
        **extra: Any,
    ) -> None:
        logger.info("Sampling: %s", sampled)
        pass

    def record_sample_completed(self, **extra: Any) -> None:
        pass

    def record_error(self, msg: str, error: Exception | None, **kwargs: Any) -> None:
        pass

    def record_extra(self, data: Any) -> None:
        pass

    def record_final_report(self, final_report: Any) -> None:
        pass

    def evalboard_url(self, view: Literal["run", "monitor"]) -> str | None:
        return None


@chz.chz
class _DummyRecorderConfig(RecorderConfig):
    async def factory(self, spec: EvalSpec, num_tasks: int) -> RecorderProtocol:
        return _DefaultDummyRecorder(run_spec=self._make_default_run_spec(spec))


class LibraryConfig:
    """
    Hooks to configure parts of the nanoeval library. Shared across all runs in the process.
    Useful for implementing interop with other libraries.

    As a normal user, you shouldn't need to change anything here.
    """

    async def send_user_notification(self, message: str, extra: str | None = None) -> None:
        """
        Notify the user when the eval starts/stops. Think of it as a slack hook!

        message = top level message
        extra = replies in thread
        """
        logger.warning(
            "No slack integration configured, so not sending user notification",
            message=message,
            extra=extra,
        )

    def on_logging_setup(self) -> None:
        # Set up structlog according to https://www.structlog.org/en/stable/standard-library.html
        # Basically, we convert structlogs to logging-style record and then process them using
        # structlog formatters into json for humio, and console for stdout
        structlog.configure(
            processors=[
                # Prepare event dict for `ProcessorFormatter`.
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

    @contextmanager
    def set_recorder_context(
        self, rec: RecorderProtocol, sample_id: str, group_id: str
    ) -> Generator[None, None, None]:
        yield

    def get_dummy_recorder(self, log: bool) -> RecorderConfig:
        return _DummyRecorderConfig()

    def writable_root_dir(self) -> str:
        return str(root_dir())

    def get_slack_tqdm(self, username: str | None) -> Any | None:
        logger.warning("No slack integration configured, so not using slack-tqdm")
        return None

    def compute_default_metrics(
        self,
        # (instance, attempt, answer_group_id [int])
        samples_df: pd.DataFrame,
        # (instance, answer_group_id [int], is_correct)
        answer_group_correctness_df: pd.DataFrame,
    ) -> dict[str, float | str | dict[Any, Any]]:
        # TODO add more metrics
        return {
            "accuracy": (
                samples_df.merge(answer_group_correctness_df, on=["instance", "answer_group_id"])
                .groupby("instance")["is_correct"]
                .mean()
                .mean()
            )
        }


_LIBRARY_CONFIG = LibraryConfig()


def get_library_config() -> LibraryConfig:
    return _LIBRARY_CONFIG


def set_library_config(hooks: LibraryConfig) -> None:
    """
    To change the default library config, set before calling any nanoeval methods:

    set_library_config(your_hooks_here)
    """
    global _LIBRARY_CONFIG
    _LIBRARY_CONFIG = hooks
