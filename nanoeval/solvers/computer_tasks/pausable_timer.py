from __future__ import annotations

import asyncio
import logging
from contextlib import ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from functools import cached_property
from typing import AsyncGenerator, Generator

from typing_extensions import override

from nanoeval.asyncio_utils import HasAsyncContextManager

logger = logging.getLogger(__name__)


class NamedTimeoutError(asyncio.TimeoutError):
    timeout_type: str

    def __init__(self, timeout_type: str, message: str):
        self.timeout_type = timeout_type
        super().__init__(message)


_MAX_TIME_SENTINEL = 100_000_000


_all_running_timers: ContextVar[frozenset[PausableTimer]] = ContextVar(
    "_all_running_timers", default=frozenset()
)


@contextmanager
def pause_all_pausable_timers() -> Generator[None, None, None]:
    timers = _all_running_timers.get()
    logger.info("Found %d ongoing timers", len(timers))
    with ExitStack() as stack:
        for timer in timers:
            stack.enter_context(timer.pause())
        yield


class PausableTimer(HasAsyncContextManager):
    def __init__(self, name: str, timeout_seconds: float):
        self.name = name
        self.timeout_seconds = timeout_seconds
        assert self.timeout_seconds < _MAX_TIME_SENTINEL, (
            "the world never imagined such long timeouts, this will break underlying pausability implementation"
        )

    @cached_property
    def timer(self) -> asyncio.Timeout:
        return asyncio.timeout(self.timeout_seconds)

    @property
    def remaining(self) -> float:
        loop = asyncio.get_running_loop()
        deadline = self.timer.when()
        assert deadline, "Timer is not scheduled yet"
        delta = deadline - loop.time()
        assert delta <= self.timeout_seconds, (
            f"Timer is paused (or a bug), got {delta=}, {deadline=}"
        )
        return delta

    @property
    def elapsed(self) -> float:
        return self.timeout_seconds - self.remaining

    @contextmanager
    def pause(self) -> Generator[None, None, None]:
        """
        Pauses the timer for the duration of the context manager.
        """
        assert not self.timer.expired(), "Cannot pause timer if it already is done"
        loop = asyncio.get_running_loop()
        remaining = self.remaining

        # Pause the timer by rescheduling it super far into the future
        logger.info("Pausing %s timer at %.2f seconds", self.name, self.elapsed)
        self.timer.reschedule(loop.time() + _MAX_TIME_SENTINEL)

        try:
            yield
        finally:
            # Resume the timer at the right time
            self.timer.reschedule(loop.time() + remaining)
            logger.info(
                "Resumed %s timer at %.2f seconds (actual time elapsed %.2f)",
                self.name,
                self.elapsed,
                loop.time() - self.start_time,
            )
            assert self.remaining <= self.timeout_seconds

    @override
    @asynccontextmanager
    async def _context(self) -> AsyncGenerator[None, None]:
        loop = asyncio.get_running_loop()
        self.start_time = loop.time()
        # Add self to the set of running timers
        token = _all_running_timers.set(_all_running_timers.get() | {self})
        try:
            async with self.timer:
                yield
        except TimeoutError as e:
            if self.timer.expired():
                # I think it was from our happy timer
                logger.warning(
                    "⏱️ Timeout %s of %.2f seconds exceeded", self.name, self.timeout_seconds
                )
                raise NamedTimeoutError(
                    self.name, f"Timeout {self.name} of {self.timeout_seconds} seconds exceeded"
                ) from e
            else:
                raise
        finally:
            _all_running_timers.reset(token)
