from __future__ import annotations

import asyncio
import logging
import random
import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import aiomonitor

logger = logging.getLogger(__name__)


@contextmanager
def _lock_and_yield_port() -> Generator[int, None, None]:
    ports_dir = Path("/tmp/nanoeval/ports")
    ports_dir.mkdir(parents=True, exist_ok=True)
    while True:
        port = random.randint(10000, 20000)
        port_file = ports_dir / str(port)
        try:
            with open(port_file, "x"):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                yield port
                break
        except (FileExistsError, OSError):
            continue
        finally:
            if port_file.exists():
                port_file.unlink()


@contextmanager
def start_aiomonitor() -> Generator[str, None, None]:
    with (
        _lock_and_yield_port() as p1,
        _lock_and_yield_port() as p2,
        _lock_and_yield_port() as p3,
        aiomonitor.start_monitor(
            asyncio.get_running_loop(), port=p1, console_port=p2, webui_port=p3
        ),
    ):
        logger.info(
            "Started aiomonitor on localhost:%d. To connect, run `python3 -m aiomonitor.cli -p %d`",
            p1,
            p1,
        )
        yield f"localhost:{p1}"
