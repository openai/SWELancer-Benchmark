from __future__ import annotations

import asyncio
import functools
import os
import subprocess
import threading
import traceback
from contextlib import AsyncExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, ContextManager, Generator, Generic, TypeVar, cast

import aiodebug.hang_inspection
import aiodebug.log_slow_callbacks
import blobfile as bf
import dill
import psutil
import structlog.stdlib
from structlog.contextvars import bound_contextvars

import nanoeval._db as db
from nanoeval import monitor as monitor
from nanoeval._aiomonitor import start_aiomonitor
from nanoeval._db import as_default_db, default_db
from nanoeval._loop_watcher import start_loop_watcher
from nanoeval._multiprocessing_utils import get_loky_executor, multiprocess_stop_signal
from nanoeval._persistent_db import PersistentDb
from nanoeval.eval import EvalSpec, RetryableSystemError, RunnerArgs, Task
from nanoeval.fs_paths import stacktrace_root_dir
from nanoeval.library_config import LibraryConfig, get_library_config, set_library_config
from nanoeval.recorder import RecorderProtocol, set_default_recorder
from nanoeval.setup import global_exit_stack, nanoeval_logging, properly_closed_thread_pool

logger = structlog.stdlib.get_logger(component=__name__)


@dataclass
class ExecutorExceptionWrapper:
    exception: Exception
    traceback: str


T = TypeVar("T")


@dataclass
class _ContextManagerSemaphore(Generic[T]):
    """Usable in async contexts only. Turns any context manager into a reentrant one that closes once the last user exits."""

    ctx: ContextManager[T]
    current: int = 0

    def __enter__(self) -> ContextManager[T]:
        if self.current == 0:
            self.ctx.__enter__()

        self.current += 1

        return self.ctx

    def __exit__(self, *args: Any) -> None:
        self.current -= 1
        if self.current == 0:
            self.ctx.__exit__(*args)


_record_ctxs: dict[str, _ContextManagerSemaphore[RecorderProtocol]] = dict()


async def _eval_task(recorder: RecorderProtocol, spec: EvalSpec, task: Task) -> None:
    group_id = task.question_id + "." + str(task.attempt_id) + "." + str(task.retry_idx)
    group_id_suffix = f"{task.attempt_id}.{task.retry_idx}"

    async with AsyncExitStack() as stack:
        # Create a shared recorder ctx for this run_id
        if recorder.run_spec.run_id not in _record_ctxs:
            _record_ctxs[recorder.run_spec.run_id] = _ContextManagerSemaphore(recorder)
        stack.enter_context(_record_ctxs[recorder.run_spec.run_id])

        stack.enter_context(
            set_default_recorder(
                recorder,
                sample_id=task.question_id,
                group_id=group_id_suffix,
            )
        )
        stack.enter_context(
            bound_contextvars(
                run_id=recorder.run_spec.run_id,
                run_set_id=recorder.run_spec.run_set_id,
                db_path=str(db.default_db.get().path),
                group_id=group_id,
            )
        )

        # Start the evals
        try:
            try:
                result = await spec.eval.evaluate(task)
            except asyncio.CancelledError as e:
                raise RetryableSystemError(
                    "Nanoeval task was canceled. This is not allowed (typically symptomatic of a bug) and will trigger a task restart."
                ) from e

            await asyncio.to_thread(recorder.record_sample_completed)

            with db.conn() as conn:
                conn.execute(
                    """
                    UPDATE task
                    SET end_time = ?, result = ?
                    WHERE eval_id = ? AND group_id = ?
                    """,
                    (
                        datetime.now(tz=timezone.utc),
                        dill.dumps(result),
                        recorder.run_spec.run_id,
                        group_id,
                    ),
                )
                conn.commit()
                logger.info("Saved result to %s.%s", recorder.run_spec.run_id, group_id)

        except RetryableSystemError as e:
            # Save this exception to the monitor. Don't crash. Main process will automatically
            # requeue the task.
            with db.conn() as conn:
                conn.execute(
                    """
                        UPDATE task
                        SET end_time = ?, result = ?
                        WHERE eval_id = ? AND group_id = ?
                        """,
                    (
                        datetime.now(tz=timezone.utc),
                        dill.dumps(
                            ExecutorExceptionWrapper(exception=e, traceback=traceback.format_exc())
                        ),
                        recorder.run_spec.run_id,
                        group_id,
                    ),
                )
                conn.commit()

            # Save the error on evalboard
            await asyncio.to_thread(
                recorder.record_error, "[nanoeval] _evaluate_episode terminated with error", e
            )
        except BaseException as e:
            # Save the error on evalboard and raise (this kills the whole job)
            await asyncio.to_thread(
                recorder.record_error,
                "[nanoeval] _evaluate_episode terminated with error",
                cast(Exception, e),
            )
            raise


@functools.cache
def _get_recorder_cached(run_id: str) -> RecorderProtocol:
    with db.conn() as conn:
        cursor = conn.execute(
            """
            SELECT recorder
            FROM eval
            WHERE run_id = ?
            """,
            (run_id,),
        )
        recorder_data = cursor.fetchone()[0]
    return db.cached_deserialize(recorder_data)


def _maybe_pull_task_from_queue() -> tuple[EvalSpec, Task, RecorderProtocol] | None:
    # Pull tasks from the monitor queue
    with db.conn() as conn:
        # Enforce global concurrency limit
        num_running = conn.execute(
            """
            SELECT COUNT(*) FROM task WHERE executor_pid IS NOT NULL and result IS NULL;
            """
        ).fetchone()[0]
        try:
            max_concurrency = int(
                conn.execute(
                    """
                select value from metadata where key = 'max_concurrency';
                """
                ).fetchone()[0]
            )
        except TypeError:
            logger.exception("Failed to retrieve max_concurrency from metadata")
            return None

        continue_ok = num_running < max_concurrency

        if not continue_ok:
            logger.info(
                "Max concurrency reached, sleeping. num_running=%s >= max concurrency=%s",
                num_running,
                max_concurrency,
            )
            return None

        conn.execute("BEGIN EXCLUSIVE;")  # Start the transaction
        try:
            # Step 3: Select the task
            cursor = conn.execute(
                """
                SELECT task.rowid
                FROM task
                JOIN eval ON task.eval_id = eval.run_id
                -- Not already being executed
                WHERE task.executor_pid IS NULL AND task.result IS NULL
                -- Ensure concurrency limit on this executor is respected
                AND (SELECT COUNT(*) FROM task WHERE eval_id = task.eval_id AND task.executor_pid = ? AND task.result is NULL) < eval.concurrency
                ORDER BY task.eval_id
                LIMIT 1;
                """,
                (os.getpid(),),
            )
            task_row = cursor.fetchone()

            # Step 4: Handle no available tasks
            if task_row is None:
                conn.execute("ROLLBACK;")
                logger.debug("No tasks to evaluate, sleeping...")
                return None

            # Step 5: Update the selected task
            task_rowid = task_row[0]
            conn.execute(
                """
                UPDATE task
                SET executor_pid = ?, start_time = ?
                WHERE rowid = ?;
                """,
                (os.getpid(), datetime.now(tz=timezone.utc), task_rowid),
            )

            # Step 6: Retrieve necessary data
            data_cursor = conn.execute(
                """
                SELECT
                    task.eval_id,
                    task.task,
                    eval.spec
                FROM task
                JOIN eval ON task.eval_id = eval.run_id
                WHERE task.rowid = ?;
                """,
                (task_rowid,),
            )
            data_row = data_cursor.fetchone()

            # Step 7: Handle retrieval errors
            if data_row is None:
                conn.execute("ROLLBACK;")
                logger.error("Failed to retrieve data for task with rowid %s.", task_rowid)
                return None

            # Step 8: Commit the transaction
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")  # Rollback the transaction upon failure
            logger.exception("An error occurred")
            return None

        # Step 9: Process the retrieved data
        eval_id, task_data, spec_data = data_row
        task: Task = dill.loads(task_data)
        recorder = _get_recorder_cached(eval_id)
        assert recorder.run_spec.run_id == eval_id, (
            f"rehydrated {recorder.run_spec.run_id=} != {eval_id=}"
        )
        eval_spec: EvalSpec = db.cached_deserialize(spec_data)
        return eval_spec, task, recorder


async def _fetch_tasks_from_monitor_forever(
    stop_signal: threading.Event,
) -> AsyncGenerator[tuple[EvalSpec, Task, RecorderProtocol], None]:
    while not stop_signal.is_set():
        task = await asyncio.to_thread(_maybe_pull_task_from_queue)
        if task is not None:
            yield task
            # avoid hot-looping
            await asyncio.sleep(0)
        else:
            await asyncio.sleep(1)


async def _executor_worker_async_main(stop_signal: threading.Event) -> None:
    # Register executor with the database on startup.
    with start_aiomonitor() as aiomonitor_host, _register_with_db(aiomonitor_host):  # noqa: F821
        # run id -> eval spec. We cache the eval specs to avoid re-entering them all the time
        eval_spec_cache = dict()

        logger.info("Nanoeval evaluation worker started")

        async def process_task(eval_spec: EvalSpec, task: Task, recorder: RecorderProtocol) -> None:
            logger.info(
                "Evaluating task %s.%s.%s", task.question_id, task.attempt_id, task.retry_idx
            )
            try:
                # Only __aenter__ once in this process
                if recorder.run_spec.run_id not in eval_spec_cache:
                    eval_spec_cache[recorder.run_spec.run_id] = eval_spec
                    try:
                        await eval_spec.eval.__aenter__()
                    except AttributeError:
                        # We don't care about double-enters
                        pass
                spec = eval_spec_cache[recorder.run_spec.run_id]
                await _eval_task(recorder, spec, task)
            except BaseException as e:
                # Omg, the task threw an exception. This is not ok, nanoeval tasks should never raise unless something bad
                # happened.
                # In this case, we always want to reraise a new error and terminate the worker.
                # we use BaseException because some errors e.g. CancelledError go silently into the night. We need to
                # reraise a standard exception because we want to hard crash here.
                logger.exception("Error in process_task")
                raise RuntimeError("An evaluation task crashed with an unhandled exception") from e

        try:
            async with asyncio.TaskGroup() as tg:
                async for eval_spec, task, recorder in _fetch_tasks_from_monitor_forever(
                    stop_signal
                ):
                    tg.create_task(
                        coro=process_task(eval_spec, task, recorder),
                        name=f"executor-{task.question_id}.{task.attempt_id}.{task.retry_idx}",
                    )
        finally:
            logger.info("Worker main loop has ended, cleaning up worker")
            # Close all evals
            for spec in eval_spec_cache.values():
                await spec.eval.__aexit__(None, None, None)


@contextmanager
def _register_with_db(aiomonitor_host: str) -> Generator[None, None, None]:
    """
    Register the executor with the monitor database.
    """
    with db.conn() as conn:
        conn.execute(
            """
            INSERT INTO executor (pid, aiomonitor_host)
            VALUES (?, ?)
            """,
            (os.getpid(), aiomonitor_host),
        )
        conn.commit()
    try:
        yield
    finally:
        with db.conn() as conn:
            conn.execute(
                """
                DELETE FROM executor
                WHERE pid = ?
                """,
                (os.getpid(),),
            )
            conn.commit()


async def _executor_worker_async_entrypoint(path: str, stop_signal: threading.Event) -> Any:
    """
    Wrapper for entrypoints of spawned processes.

    For spawned processes, we normally don't want to create a large thread pool,
    but we still want cleaner logging.
    """

    with properly_closed_thread_pool(n_threads=2048):
        nanoeval_logging()
        with (
            bound_contextvars(pid=os.getpid()),
            as_default_db(PersistentDb(path=path, backup=False)) as db,
        ):
            # Turn on aiodebug to log stack traces on hangs
            stacktrace_dir = stacktrace_root_dir() / bf.basename(db.path)
            os.makedirs(stacktrace_dir, exist_ok=True)
            dumper = aiodebug.hang_inspection.start(str(stacktrace_dir), interval=10.0)
            logger.info("Saving aiodebug hang logs to", dir=stacktrace_dir)
            aiodebug.log_slow_callbacks.enable(1.0)

            try:
                async with start_loop_watcher():
                    return await _executor_worker_async_main(stop_signal=stop_signal)
            finally:
                await aiodebug.hang_inspection.stop_wait(dumper)


def _executor_worker_entrypoint(
    config: LibraryConfig, path: str, stop_signal: threading.Event
) -> None:
    """
    Entrypoint for nanoeval multiprocessing workers.
    """
    set_library_config(config)
    try:
        asyncio.run(_executor_worker_async_entrypoint(path, stop_signal))
    except Exception:
        logger.exception("Worker entrypoint failed")
        raise


@contextmanager
def _try_start_monitor_streamlit() -> Generator[None, None, None]:
    """
    Try starting the Streamlit monitor and ignore errors, but kill the process on exit.
    """
    process = subprocess.Popen(
        [
            "streamlit",
            "run",
            monitor.__file__,
            "--server.headless",
            "true",
            "--server.port",
            "8501",
        ]
    )
    try:
        yield
    finally:
        try:
            process.terminate()
        except Exception:
            logger.warning(
                "Failed to terminate Streamlit monitor (this is not a big deal)", exc_info=True
            )


async def _clean_up_dead_executors() -> None:
    """
    Clean up dead executors.
    """
    while True:
        # Fetch all subprocess pids
        pids = []
        parent_pid = os.getpid()
        parent_process = psutil.Process(parent_pid)
        for child in parent_process.children(recursive=True):
            pids.append(child.pid)

        dead_pids = []

        with db.conn() as conn:
            # For each executor, delete it if the pid is missing
            cursor = conn.execute(
                """
                SELECT pid FROM executor
                WHERE pid NOT IN ({})
                """.format(",".join("?" * len(pids))),
                pids,
            )
            to_delete = cursor.fetchall()
            for (dead_pid,) in to_delete:
                dead_pids.append(dead_pid)
                logger.info(f"Deleting dead executor entry with pid {dead_pid}")
                conn.execute(
                    """
                    DELETE FROM executor
                    WHERE pid = ?
                    """,
                    (dead_pid,),
                )
            conn.commit()

        # Move the tasks that were assigned to dead executors back to the queue
        rescheduled_tasks = 0
        with db.conn() as conn:
            # Unschedule tasks that are assigned to dead executors, do 1000 at a time to avoid killing the db forever
            while True:
                stmt = """
                UPDATE task
                SET executor_pid = NULL
                WHERE rowid IN (
                    SELECT rowid
                    FROM task
                    WHERE executor_pid NOT IN ({})
                    LIMIT 1000
                )
                    """.format(",".join("?" * len(pids)))
                cursor = conn.execute(stmt, pids)
                conn.commit()
                rescheduled_tasks += cursor.rowcount
                if cursor.rowcount == 0:
                    break

        if rescheduled_tasks > 0:
            logger.info("Reassigned %d tasks away from dead executors", rescheduled_tasks)

        await asyncio.sleep(5)


_started_executors: bool = False


async def _pass_through_executor_exceptions(executor_futures: list[asyncio.Future[Any]]) -> None:
    """
    This function exists to wait on executor futures. Executor futures should not
    crash during the lifetime of the eval unless the eval raises an exception
    that causes the executor to crash. In this case, we want to crash the main
    process too, which this function will do.
    """
    try:
        await asyncio.gather(*executor_futures)
    except Exception as e:
        raise RuntimeError(
            "An evaluation executor crashed with an unhandled exception, which should never happen. The full stacktrace is below. This crash MAY NOT HAVE COME FROM THE EVAL that raised the exception if you are running multiple evals at the same time, because all evals share a pool of executors."
        ) from e


async def ensure_executor_workers_started(runner: RunnerArgs) -> None:
    """
    Start the nanoeval executors. This function will only start the executors once,
    even if called multiple times.
    """
    global _started_executors

    if _started_executors:
        # We already started the executor
        return

    # Use the global exit stack to start all services. This exit stack is killed at
    # process exit. If any of the below tasks raise an exception, the asyncio
    # TaskGroup will cancel the main task wherever it is, and the global exit stack
    # will raise the Exception as an ExceptionGroup.
    if runner.use_monitor:
        # Start streamlit monitor
        global_exit_stack.enter_context(_try_start_monitor_streamlit())

    # TaskGroup to handle background executor polling services
    tg = await global_exit_stack.enter_async_context(asyncio.TaskGroup())

    def record_shutdown() -> None:
        logger.info("Shutting down all the executors")
        global _started_executors
        _started_executors = False

    stop_signal = (
        multiprocess_stop_signal() if runner.experimental_use_multiprocessing else threading.Event()
    )

    # We mark that we started the executor so a second call doesn't start it again.
    stop_signal.clear()
    _started_executors = True
    global_exit_stack.callback(record_shutdown)

    if runner.experimental_use_multiprocessing:
        # Start executor garbage collector (reassigns tasks away from dead executors)
        global_exit_stack.callback(tg.create_task(_clean_up_dead_executors()).cancel)

        executor = get_loky_executor(runner.num_processes)

        executor_futures = [
            asyncio.wrap_future(
                executor.submit(
                    _executor_worker_entrypoint,
                    path=default_db.get().path,
                    stop_signal=stop_signal,
                    config=get_library_config(),
                )
            )
            for _ in range(runner.num_processes or os.cpu_count() or 16)
        ]
        global_exit_stack.callback(
            tg.create_task(_pass_through_executor_exceptions(executor_futures)).cancel
        )
    else:
        # Run one task in asyncio mode - cancel it when we exit this context manager
        global_exit_stack.callback(
            tg.create_task(_executor_worker_async_main(stop_signal=stop_signal)).cancel
        )
