import asyncio
from unittest.mock import patch

import pytest

from .pausable_timer import NamedTimeoutError, PausableTimer, pause_all_pausable_timers


@pytest.mark.asyncio
async def test_enforce_timeout_exceeded() -> None:
    with patch("time.monotonic") as mock_monotonic:
        # Set the initial time
        initial_time = 100.0
        current_time = initial_time
        mock_monotonic.return_value = current_time

        # Define a sample task that will run longer than the timeout
        async def long_running_task() -> None:
            nonlocal current_time
            timer = PausableTimer(name="x", timeout_seconds=5.0)
            async with timer:
                # Advance time by 3 seconds
                current_time += 3.0
                mock_monotonic.return_value = current_time
                await asyncio.sleep(0)  # Yield control

                # Advance time by another 3 seconds (total 6 seconds)
                current_time += 3.0
                mock_monotonic.return_value = current_time
                await asyncio.sleep(1)  # Yield control, let timer expire

        # Run the task and verify that NamedTimeoutError is raised
        with pytest.raises(NamedTimeoutError) as exc_info:
            await long_running_task()

        assert exc_info.value.timeout_type == "x", (
            f"Timeout type should be 'x', got {exc_info.value.timeout_type}"
        )
        assert str(exc_info.value) == "Timeout x of 5.0 seconds exceeded", (
            f"Error message mismatch: {str(exc_info.value)}"
        )


@pytest.mark.asyncio
async def test_nested_timeouts_work_properly() -> None:
    with pytest.raises(TimeoutError) as exc_info:  # noqa: PT012
        async with PausableTimer(name="x", timeout_seconds=600):
            async with asyncio.timeout(0.0001):
                await asyncio.sleep(1)

    assert exc_info.type is TimeoutError


@pytest.mark.asyncio
async def test_pauses() -> None:
    async with PausableTimer(name="x", timeout_seconds=0.01) as t:
        with t.pause():
            await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_global_pauses() -> None:
    async with (
        PausableTimer(name="x", timeout_seconds=0.01),
        PausableTimer(name="y", timeout_seconds=0.01),
    ):
        with pause_all_pausable_timers():
            await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_enforce_timeout_not_exceeded() -> None:
    # Define a sample task that will complete before the timeout
    async def quick_task() -> None:
        timer = PausableTimer(name="x", timeout_seconds=5.0)
        async with timer:
            print("x")
            await asyncio.sleep(0.0001)  # Yield control
            print("y")

    # Run the task and verify that it completes without exception
    try:
        await quick_task()
    except NamedTimeoutError:
        pytest.fail("NamedTimeoutError was raised unexpectedly for a quick task.")
