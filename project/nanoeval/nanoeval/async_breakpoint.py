import inspect
from typing import Any, cast

from ptpython.repl import embed


async def abreakpoint() -> None:
    frame = inspect.currentframe()
    assert frame and frame.f_back
    await cast(
        Any,
        embed(
            globals=frame.f_back.f_globals,
            locals=frame.f_back.f_locals,
            return_asyncio_coroutine=True,
            patch_stdout=True,
        ),
    )
