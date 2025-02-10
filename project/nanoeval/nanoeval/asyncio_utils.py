from __future__ import annotations

import asyncio
import logging
import warnings
from contextlib import asynccontextmanager
from functools import cached_property
from types import TracebackType
from typing import Any, AsyncContextManager, AsyncGenerator, Coroutine, Self, TypeVar

T = TypeVar("T")


logger = logging.getLogger(__name__)


@asynccontextmanager
async def generator_with_cleanup(
    gen: AsyncGenerator[T, None],
) -> AsyncGenerator[AsyncGenerator[T, None], None]:
    try:
        yield gen
    finally:
        logger.debug("closing generator %s", gen)
        try:
            await gen.aclose()
        except RuntimeError:
            logger.warning("Generator closure failed, but ignoring", exc_info=True)


async def gather_with_concurrency(
    futures: list[Coroutine[Any, Any, T]], concurrency: int
) -> AsyncGenerator[T, None]:
    # Use a task group to manage cancellation
    try:
        async with asyncio.TaskGroup() as tg:
            running_tasks: set[asyncio.Task[T]] = set()

            for future in futures:
                if len(running_tasks) >= concurrency:
                    done, running_tasks = await asyncio.wait(
                        running_tasks, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in done:
                        yield task.result()
                running_tasks.add(tg.create_task(future))

            # Wait for the remaining tasks to finish
            for f in asyncio.as_completed(running_tasks):
                yield await f

    except* GeneratorExit:
        # Gets triggered when gen.aclose() is called. Cleanup would happen here.
        # Normally we don't need to catch this if no cleanup is required, but here
        # asyncio.TaskGroup() catches GeneratorExit and reraises it as a BaseExceptionGroup
        # *containing* a GeneratorExit, so we need to catch it. For discussion see
        # https://github.com/openai/openai/pull/122176/files#r1655204046
        logger.warning("Ignoring GeneratorExit (likely a spurious error from task cleanup)")


class HasAsyncContextManager:
    """
    Mixin that allows you to ergonomically define a context manager for an object.

    When you do `async with obj`, it'll call `obj.context()` and enter the context.
    """

    @asynccontextmanager
    async def _context(self) -> AsyncGenerator[None, None]:
        yield

    @cached_property
    def __context_singleton(self) -> AsyncContextManager[None]:
        return self._context()

    async def __aenter__(self) -> Self:
        await self.__context_singleton.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None:
        await self.__context_singleton.__aexit__(exc_type, exc_value, tb)
        return None


async def cancel_task(fut: asyncio.Future[Any]) -> None:
    """Cancel a future/task and await for it to finish.

    Background: the function implements a few best practices of asyncio task
    cancellation. Use this function instead of these less correct alternatives:

    1. Just `task.cancel()`. This schedules a CancelledError to be thrown into
    the task at some point in the future. Two common problems with this:
        a. If `task` reference is garbage collected before the exception is
        produced inside the task (e.g. `task = None`), the task might be just
        "silently interrupted" without any exception, skipping `finally:` and
        context manager exits.
        b. If the task has failed with any exception it will be silently hidden.
    2. `task.cancel()` followed by `await task`. This mitigates the above
    issues, but also requires catching the CancelledError propagated from the
    cancelled task, e.g.
        try:
            task.cancel()
            await task
        except CancelledError:
            pass
    This approach has a bug in case the "parent" task that calls `task.cancel()`
    is itself cancelled. The `try/except` will silently swallow the
    CancelledError leading to unexpected results.

    If the fut is already done() this is a no-op
    If everything goes well this returns None.

    If this coroutine is cancelled, we wait for the passed in argument to cancel
    but we will raise the CancelledError as per Cancellation Contract, Unless the task
    doesn't cancel correctly then we could raise other exceptions.

    If the task raises an exception during cancellation we re-raise it
    if the task completes instead of cancelling we raise a InvalidStateError
    """
    if fut.done():
        return  # nothing to do

    # Trigger future cancellation, aka throw CancelledError into the coroutine.
    fut.cancel()

    # Set if the coroutine running cancel() is itself cancelled.
    self_cancelled: asyncio.CancelledError | None = None
    while not fut.done():
        shielded = asyncio.shield(fut)
        try:
            # Blocks until fut finishes or this coroutine is attempted to
            # be cancelled.
            await asyncio.wait([shielded])
        except asyncio.CancelledError as ex:
            # This coroutine itself was cancelled.
            # We record the fact to re-raise eventually, but will wait for the
            # inner task to actually finish its cancellation.
            # Continue the `while` loop to continue catching more cancellation.
            self_cancelled = ex
        finally:
            # Ensure the result of the provided coroutine is examined to prevent
            # asyncio logger from complaining about the result ignored.
            if shielded.done() and not shielded.cancelled() and not shielded.exception():
                shielded.result()
    if fut.cancelled():
        if self_cancelled is None:
            # Happy path.
            return
        # We were cancelled also so honor the contract - return CancelledErro.
        raise self_cancelled from None

    # Some other exception thrown during cancellation
    inner_exc = fut.exception()
    if inner_exc is not None:
        raise inner_exc from None
    # fut was sent a CancelledError, but has exited w/o an exception, i.e has
    # not propagated it. This is a violation of CancelledError contract.
    warnings.warn(
        f"Task didn't raise CancelledError on cancel! {fut}",
        RuntimeWarning,
        stacklevel=1,
    )
