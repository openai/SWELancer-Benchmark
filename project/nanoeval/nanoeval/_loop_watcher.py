import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from nanoeval.asyncio_utils import cancel_task

logger = logging.getLogger(__name__)


_WAIT_TIME = 60.0


async def _loop_watcher() -> None:
    last_tick = time.monotonic()
    while True:
        now = time.monotonic()

        if now - last_tick > _WAIT_TIME * 1.25:
            logger.error(
                "Expected loop tick every %d seconds, but it actually took %.3f seconds",
                _WAIT_TIME,
                now - last_tick,
            )
        else:
            logger.info("Loop tick took %.3f seconds", now - last_tick)

        last_tick = now
        await asyncio.sleep(_WAIT_TIME)


@asynccontextmanager
async def start_loop_watcher() -> AsyncGenerator[None, None]:
    task = asyncio.create_task(_loop_watcher())
    try:
        yield
    finally:
        await cancel_task(task)
