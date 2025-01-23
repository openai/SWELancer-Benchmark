from __future__ import annotations

import functools
import logging
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, AsyncGenerator, Generator

import blobfile as bf
import dill

from nanoeval._evallib_vendor.run_spec_base import uuid
from nanoeval._persistent_db import PersistentDb
from nanoeval.fs_paths import writable_root_dir

logger = logging.getLogger(__name__)


default_db: ContextVar[PersistentDb] = ContextVar("default_db")


# Not currently used by default, but you can set it via `python3 -m nanoeval.bin.concurrency`
_INITIAL_MAX_CONCURRENCY = 1_000_000


@contextmanager
def as_default_db(db: PersistentDb) -> Generator[PersistentDb, None, None]:
    token = default_db.set(db)
    try:
        yield db
    finally:
        default_db.reset(token)


@asynccontextmanager
async def open_run_set_db(
    backup: bool, run_set_id: str | None = None
) -> AsyncGenerator[PersistentDb, None]:
    """
    nanoeval stores run state in a sqlite database that gets periodically backed up to Azure Blob Storage.

    Args:
        backup: Whether to backup the database to Azure Blob Storage in this process. Enable if you are the main process.
        run_set_id: Specify a run set ID. Use this to load a preexisting database.
    """

    if not run_set_id:
        run_set_id = uuid()

    path = bf.join(writable_root_dir(), "run_state", run_set_id + ".db")

    # No need to double-open the database
    try:
        if default_db.get().path == path:
            logger.info("Database already opened at %s, reusing", path)
            yield default_db.get()
            return
    except LookupError:
        pass

    async with PersistentDb(path=path, backup=backup) as db:
        with db.conn() as conn:
            # https://til.simonwillison.net/sqlite/enabling-wal-mode
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS eval (
                    run_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    spec BLOB NOT NULL,
                    recorder BLOB NOT NULL,
                    concurrency INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executor (
                    pid INTEGER PRIMARY KEY,
                    aiomonitor_host STRING NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task (
                    eval_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    task BLOB NOT NULL,
                    result BLOB,
                    executor_pid INTEGER,
                    FOREIGN KEY(eval_id) REFERENCES eval(run_id),
                    UNIQUE(eval_id, group_id)
                )
                """
            )

            # The task table can be very large, so we add an index for the executor worker's sql query
            # Without this index, evals become very slow over time as the task table grows (result is not null anymore)
            conn.execute(
                """
                -- Used to pull new tasks
                CREATE INDEX IF NOT EXISTS task_result_executor_pid_idx ON task(result, executor_pid)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS task_executor_pid_idx ON task(executor_pid);
            """
            )

            # Create a KV metadata table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            # Insert the run_set_id into the metadata table so .evaluation() can read it later
            conn.execute(
                """
                INSERT INTO metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?
                """,
                ("run_set_id", run_set_id, run_set_id),
            )
            conn.execute(
                """
                INSERT INTO metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?
                """,
                ("max_concurrency", _INITIAL_MAX_CONCURRENCY, _INITIAL_MAX_CONCURRENCY),
            )
            conn.commit()

        with as_default_db(db):
            yield db


@contextmanager
def conn() -> Generator[sqlite3.Connection, None, None]:
    with default_db.get().conn() as c:
        yield c


@functools.cache
def cached_deserialize(d: bytes) -> Any:
    return dill.loads(d)
