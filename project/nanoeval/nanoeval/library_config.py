from __future__ import annotations

import functools
import logging
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Literal, Self

import pandas as pd
import structlog
from structlog.typing import EventDict

import chz
from nanoeval.recorder_protocol import BasicRunSpec, RecorderConfig, RecorderProtocol

if TYPE_CHECKING:
    from nanoeval.eval import EvalSpec


ENV_NANOEVAL_LOG_ALL = "NANOEVAL_LOG_ALL"


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


def _rename_field(
    old: str, new: str, logger: logging.Logger, name: str, event_dict: EventDict
) -> EventDict:
    del logger, name

    if value := event_dict.get(old):
        event_dict[new] = value
        del event_dict[old]
    return event_dict


def _remove_all_fields_except(
    to_keep: list[str], logger: logging.Logger, name: str, event_dict: EventDict
) -> EventDict:
    del logger, name

    for key in list(event_dict.keys()):
        if key not in to_keep:
            del event_dict[key]
    return event_dict


class PrintOrWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno > logging.INFO or (
            os.environ.get(ENV_NANOEVAL_LOG_ALL) and record.levelno == logging.INFO
        ):
            return True

        return isinstance(record.msg, dict) and record.msg.get("_print", False)


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

    def setup_logging(self) -> None:
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

        # Remove all StreamHandlers from the root logger
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler):
                logging.getLogger().removeHandler(handler)

        handler = logging.StreamHandler()
        # Use OUR `ProcessorFormatter` to format all `logging` entries to stdout.
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.MaybeTimeStamper(fmt="iso"),
                    functools.partial(
                        _remove_all_fields_except,
                        ["timestamp", "level", "event", "component", "exc_info"],
                    ),
                    structlog.dev.ConsoleRenderer(),
                ],
                # logger -> structlog transforms
                foreign_pre_chain=[
                    structlog.stdlib.add_logger_name,
                    partial(_rename_field, "logger", "component"),
                    partial(_rename_field, "logger_name", "component"),
                    partial(_rename_field, "log", "event"),
                    structlog.stdlib.ExtraAdder(),
                ],
            )
        )

        handler.addFilter(PrintOrWarningFilter())
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    @contextmanager
    def set_recorder_context(
        self, rec: RecorderProtocol, sample_id: str, group_id: str
    ) -> Generator[None, None, None]:
        yield

    def get_dummy_recorder(self, log: bool) -> RecorderConfig:
        return _DummyRecorderConfig()

    def get_default_recorder(self) -> RecorderConfig:
        from nanoeval.json_recorder import json_recorder

        return json_recorder()

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
