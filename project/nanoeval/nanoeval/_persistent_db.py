import asyncio
import logging
import os
import sqlite3
import tempfile
import time
from contextlib import AsyncExitStack, closing, contextmanager
from pathlib import Path
from typing import Any, Generator, Self

import blobfile as bf
import boostedblob as bbb

import chz
from nanoeval.fs_paths import database_dir

logger = logging.getLogger(__name__)


def _human_readable_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"


_IS_CI = "BUILDKITE" in os.environ


@chz.chz
class PersistentDb:
    """
    SQLite database that is backed up to Azure Blob Storage. It is referenced canonically by an SSPath
    object, but it stores the local database in /dev/shm. Useful for NON CRITICAL data where losing
    ~5 min of data is no big deal.
    """

    path: str
    backup: bool = True

    @chz.init_property
    def _upload_lock(self) -> asyncio.Lock:
        return asyncio.Lock()

    @chz.init_property
    def _exit_stack(self) -> AsyncExitStack:
        return AsyncExitStack()

    @chz.init_property
    def database_file(self) -> Path:
        return database_dir() / f"{bf.basename(self.path)}"

    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Use like:

        ```python
        with db.conn() as conn: # will automatically close connection and commit transaction
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test DEFAULT VALUES")
        ```
        """

        with (
            # Close db file
            closing(sqlite3.connect(self.database_file, timeout=600)) as conn,
            # Start a transaction
            conn,
        ):
            yield conn

    @bbb.ensure_session
    async def _restore(self) -> None:
        if _IS_CI:
            logger.info("CI environment, skipping db restore")
            return

        if not self.backup:
            return

        if not bf.exists(self.database_file):
            # Download the database
            logger.info("Downloading database %s", self.path)
            try:
                async with bbb.BoostExecutor(16) as executor:
                    await bbb.copyfile(self.path, str(self.database_file), executor)

                db_size = bf.stat(self.database_file).size
                logger.info("Downloaded db size: %s", _human_readable_size(db_size))
            except FileNotFoundError:
                logger.info("Database %s not found, skipping", self.path)
                return

    async def _upload(self) -> None:
        if _IS_CI:
            logger.info("CI environment, skipping db restore")
            return

        if not self.backup:
            return

        async with self._upload_lock:
            logger.info("Uploading database %s -> %s", self.database_file, self.path)
            start = time.monotonic()

            with tempfile.NamedTemporaryFile() as temp:
                async with bbb.BoostExecutor(16) as executor:
                    # TODO(kevinliu) move to a different thread to avoid blocking
                    with self.conn() as conn, closing(sqlite3.connect(temp.name)) as temp_conn:
                        conn.backup(temp_conn)

                    logger.info("Backed up database to %s", temp.name)
                    await bbb.copyfile(temp.name, self.path, executor, overwrite=True)
                    logger.info(
                        "Uploaded database %s in %s sec", self.path, time.monotonic() - start
                    )

    async def _upload_task(self) -> None:
        while True:
            await asyncio.sleep(300)
            await self._upload()

    async def __aenter__(self) -> Self:
        await self._restore()
        await self._exit_stack.__aenter__()

        self._exit_stack.callback(asyncio.create_task(self._upload_task()).cancel)

        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        logger.info("Closing db...")
        await self._exit_stack.__aexit__(exc_type, exc, tb)
        await self._upload()
