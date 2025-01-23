from __future__ import annotations

import asyncio
import logging
import os
import resource
from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack, contextmanager
from functools import partial
from typing import Any, Coroutine, Generator

import structlog
from structlog.contextvars import bound_contextvars
from structlog.types import EventDict

from nanoeval._aiomonitor import start_aiomonitor
from nanoeval.library_config import get_library_config

logger = structlog.stdlib.get_logger(component=__name__)


global_exit_stack = AsyncExitStack()
"""
The global exit stack can be used to represent closable global state which will be
cleaned up when the program exits.
"""


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
            os.environ.get("NANOEVAL_LOG_ALL") and record.levelno == logging.INFO
        ):
            return True

        return isinstance(record.msg, dict) and record.msg.get("_print", False)


def nanoeval_logging() -> None:
    logging.captureWarnings(True)
    get_library_config().on_logging_setup()
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
                partial(_remove_all_fields_except, ["timestamp", "level", "event", "component"]),
                structlog.dev.ConsoleRenderer(),
            ],
            # logger -> structlog transforms
            foreign_pre_chain=[
                structlog.stdlib.add_logger_name,
                partial(_rename_field, "logger", "component"),
                partial(_rename_field, "logger_name", "component"),
                structlog.stdlib.ExtraAdder(),
            ],
        )
    )

    handler.addFilter(PrintOrWarningFilter())
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


@contextmanager
def properly_closed_thread_pool(n_threads: int = 10_000) -> Generator[None, None, None]:
    # Use a very large thread pool executor so we can saturate engines
    executor = ThreadPoolExecutor(n_threads)
    try:
        asyncio.get_running_loop().set_default_executor(executor)
        yield
    finally:
        # Properly close the thread pool executor
        # See the great post here: https://www.roguelynn.com/words/asyncio-sync-and-threaded/
        logger.info("Shutting down executor")
        executor.shutdown(wait=False)

        logging.info(f"Releasing {len(executor._threads)} threads from executor")
        for thread in executor._threads:
            try:
                thread._tstate_lock.release()  # type: ignore
            except Exception:
                pass


async def _main_process_async_entrypoint(entry: Coroutine[Any, Any, None]) -> None:
    with properly_closed_thread_pool():
        nanoeval_logging()
        async with global_exit_stack:
            with (
                # Must be inside the thread pool executor, because we don't
                # want to close the thread pool executor before uploading logs
                bound_contextvars(pid=os.getpid()),
                start_aiomonitor(),
            ):
                await entry


def nanoeval_entrypoint(entry: Coroutine[Any, Any, None]) -> None:
    """
    Use at the beginning of your eval file. This configures nanoeval in high
    performance + easy debugging mode. It sets up:

    * default asyncio thread pool executor of 10_000 threads, to better saturate
      models (see https://openai-research.slack.com/archives/C0604914XGT/p1715131991703489)
    """

    # Raise the open file limit (so we don't run out of file descriptors)
    # We do this by default because the default concurrency is 2048, and we
    # open a logging file for each attempt by default. So we'll use min
    # 2048 fds already.
    resource.setrlimit(resource.RLIMIT_NOFILE, (131_072, 131_072))

    asyncio.run(_main_process_async_entrypoint(entry))
