from contextlib import AsyncExitStack
import asyncio


async def _oops_crash() -> None:
    await asyncio.sleep(0.1)
    raise RuntimeError("woops")


async def main() -> None:
    async with AsyncExitStack() as stack:
        tg = await stack.enter_async_context(asyncio.TaskGroup())
        raise RuntimeError("oops")
        print("vroom!")
        await asyncio.sleep(30)
        print("done!")


if __name__ == "__main__":
    asyncio.run(main())
