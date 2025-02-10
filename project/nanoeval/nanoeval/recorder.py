from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Generator

from nanoeval.library_config import get_library_config
from nanoeval.recorder_protocol import RecorderConfig, RecorderProtocol

logger = logging.getLogger(__name__)


recorder: ContextVar[RecorderProtocol] = ContextVar("recorder")


def get_recorder() -> RecorderProtocol:
    return recorder.get()


@contextmanager
def set_default_recorder(
    rec: RecorderProtocol, sample_id: str, group_id: str
) -> Generator[None, None, None]:
    """
    Context manager to set the default recorder for the current thread.
    """
    token = recorder.set(rec)
    try:
        with get_library_config().set_recorder_context(rec, sample_id, group_id):
            yield
    finally:
        recorder.reset(token)


def dummy_recorder(log: bool = True) -> RecorderConfig:
    """
    Returns a dummy recorder that does nothing.
    """
    return get_library_config().get_dummy_recorder(log)
