import asyncio

import pytest

from nanoeval.solvers.computer_tasks.limits import LimitsHelper
from nanoeval.solvers.computer_tasks.pausable_timer import NamedTimeoutError


@pytest.mark.asyncio
async def test_unrelated_timeouts() -> None:
    with pytest.raises(TimeoutError) as exc_info:  # noqa: PT012
        limits = LimitsHelper()
        async with limits.enforce_timeout("test", 0.1):
            async with asyncio.timeout(0.01):
                await asyncio.sleep(2)

    assert type(exc_info.value) is TimeoutError

    with pytest.raises(NamedTimeoutError, match="Timeout test of 0.01 seconds exceeded"):  # noqa: PT012
        limits = LimitsHelper()
        async with limits.enforce_timeout("test", 0.01):
            async with asyncio.timeout(0.5):
                await asyncio.sleep(1)
