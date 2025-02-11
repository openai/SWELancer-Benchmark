from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import AsyncGenerator, Callable

import chz
from nanoeval.solvers.computer_tasks.pausable_timer import PausableTimer

logger = logging.getLogger(__name__)


class ActionLimitExceededError(Exception):
    pass


class SystemErrorDetected(Exception):
    name: str
    text: str


current_timer: ContextVar[PausableTimer | None] = ContextVar("current_timer", default=None)


@chz.chz
class LimitsHelper:
    """
    Defines limits for a python coding task.
    """

    max_actions: int = 100
    max_time_seconds: int = 3600
    grading_timeout: int = 600
    exception_handling_timeout: int = 600
    total_sample_timeout: int = 3600 * 4
    validate_connection_limit: int = 60 * 5

    @chz.validate
    def _timers_in_order(self) -> None:
        assert self.max_time_seconds > 0
        assert self.grading_timeout > 0
        assert self.exception_handling_timeout > 0
        assert self.total_sample_timeout > 0
        assert self.validate_connection_limit > 0

        assert (
            self.max_time_seconds + self.exception_handling_timeout <= self.total_sample_timeout
        ), "max_time_seconds + exception_handling_timeout should be less than total_sample_timeout"

    @asynccontextmanager
    async def enforce_timeout(
        self, timeout_type: str, timeout_seconds: float
    ) -> AsyncGenerator[None, None]:
        """
        Enforce a timeout. Raises a NamedTimeoutError if the timeout is exceeded.
        """
        token = current_timer.set(PausableTimer(timeout_type, timeout_seconds))
        try:
            assert (c := current_timer.get()) is not None
            async with c:
                yield
        finally:
            current_timer.reset(token)

    @asynccontextmanager
    async def enforce_rollout_limits(self) -> AsyncGenerator[Callable[[], None], None]:
        """
        Enforce the rollout (max actions, max time) set in this class. Raises:

        - ActionLimitExceededError if the number of actions exceeds max_actions.
        - asyncio.TimeoutError if the time limit is exceeded.
        """

        num_actions = 0
        async with self.enforce_timeout("max_time", self.max_time_seconds):

            def increment_actions() -> None:
                nonlocal num_actions
                num_actions += 1

                if num_actions >= self.max_actions:
                    raise ActionLimitExceededError("Exceeded max actions = %d!" % self.max_actions)

            yield increment_actions
