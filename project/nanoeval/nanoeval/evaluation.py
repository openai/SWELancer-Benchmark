from __future__ import annotations

import asyncio
import random
import time
import traceback
from asyncio import CancelledError
from contextlib import AsyncExitStack
from datetime import datetime
from pprint import pformat
from typing import Any

import dill
import structlog.stdlib
from structlog.contextvars import bound_contextvars
from tqdm import tqdm

import chz
import nanoeval._db as db
from nanoeval._db import cached_deserialize, default_db, open_run_set_db
from nanoeval._executor_worker import ExecutorExceptionWrapper, ensure_executor_workers_started
from nanoeval.eval import Eval, EvalSpec, RetryableSystemError, RunnerArgs, Task
from nanoeval.library_config import get_library_config
from nanoeval.recorder import RecorderProtocol, dummy_recorder
from nanoeval.setup import global_exit_stack

logger = structlog.stdlib.get_logger(component=__name__)


async def _make_pbar(spec: EvalSpec, n_tasks: int, recorder: RecorderProtocol) -> Any:
    desc = f"{spec.eval.get_name()[-16:]} (r_id={recorder.run_spec.run_id}, m={(await spec.model_name())[-16:]})"

    if spec.runner.enable_slackbot and (
        t := get_library_config().get_slack_tqdm(username=spec.runner.slack_name or None)
    ):
        return t(total=n_tasks, desc=desc, dynamic_ncols=True)

    return tqdm(
        total=n_tasks,
        dynamic_ncols=True,
        desc=desc,
    )


def _create_clean_results(results: list[tuple[Task, Any]]) -> list[tuple[Task, Any]]:
    """Return only the latest attempt for each task."""

    latest: dict[tuple[str, int], tuple[Task, Any]] = {}
    for task, result in results:
        key = (task.question_id, task.attempt_id)
        current = latest.get(key)
        if current is None or task.retry_idx > current[0].retry_idx:
            latest[key] = (task, result)

    clean_results = list(latest.values())

    # Sanity check the deduplication function.
    seen_tasks: set[tuple[str, int]] = set()
    for task, _ in clean_results:
        task_id = (task.question_id, task.attempt_id)
        assert task_id not in seen_tasks, (
            f"Duplicate task found: {task_id}. This is a bug in nanoeval."
        )
        seen_tasks.add(task_id)

    return clean_results


async def _format_slack_message(
    recorder: RecorderProtocol, spec: EvalSpec, start_time: float, title: str, done: bool
) -> str:
    link = recorder.evalboard_url("run" if done else "monitor")
    msg = f"""
nanoeval: {title}

*Name*: `{spec.eval.get_name()}`
*Run ID*: `{recorder.run_spec.run_id}` (link {link or "[unknown]"})
*Run Set ID*: `{recorder.run_spec.run_set_id}`
*Model*: `{await spec.model_name()}`
*Elapsed*: {time.monotonic() - start_time:.2f}s
""".strip()

    if not done:
        msg += f"\n\nIf your run crashes, use this command to resume: `python3 -m nanoeval.bin.resume run_set_id={db.get_resume_run_set_id()}`"

    return msg


async def run_eval_in_database(run_id: str) -> dict[str, Any]:
    """
    Run an evaluation based off a run_id by reading all state from the database.

    This is a function used by `nanoeval.run` and `nanoeval.extras.resume` to resume
    an eval run. You should not call this function directly.
    """
    start_time = time.monotonic()

    # Deserialize the spec and recorder
    with db.conn() as conn:
        cursor = conn.execute(
            """
            SELECT spec, recorder
            FROM eval
            WHERE run_id = ?
            """,
            (run_id,),
        )
        row = cursor.fetchone()

    assert row, f"Run ID {run_id} not found in database"
    spec: EvalSpec = cached_deserialize(row[0])
    recorder: RecorderProtocol = cached_deserialize(row[1])

    try:
        logger.info(
            f"\033[36m\033[1mEvalboard Monitor: {recorder.evalboard_url('monitor') or 'unknown, add in pr?'}\033[0m",
            _print=True,
        )
        if spec.runner.enable_slackbot:
            await get_library_config().send_user_notification(
                await _format_slack_message(
                    recorder, spec, start_time, "🧪 Eval Started!", done=False
                ),
            )

        summary = {}  # noqa
        async with AsyncExitStack() as stack:
            with db.conn() as conn:
                cur = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM task
                    WHERE eval_id = ?
                    """,
                    (recorder.run_spec.run_id,),
                )
                res = cur.fetchone()
                assert res is not None, "No results from count query"
                num_tasks: int = res[0]
            pbar = stack.enter_context(await _make_pbar(spec, num_tasks, recorder))
            stack.enter_context(
                bound_contextvars(
                    run_id=recorder.run_spec.run_id,
                    run_set_id=recorder.run_spec.run_set_id,
                    db_path=str(db.default_db.get().path),
                )
            )

            logger.info("Starting evaluation of tasks")
            # Start the executor workers if not already started in the current driver process
            await ensure_executor_workers_started(spec.runner)

            results: list[tuple[Task, Any]] = []
            last_summary_time = time.monotonic()

            # Wait for the results
            while True:
                results.clear()
                with db.conn() as conn:
                    cur = conn.execute(
                        """
                        SELECT COUNT(*)
                        FROM task
                        WHERE eval_id = ?
                        """,
                        (recorder.run_spec.run_id,),
                    )
                    res = cur.fetchone()
                    assert res is not None, "No results from count query"
                    num_tasks = res[0]

                # Fetch results from the queue (result IS NOT NULL)
                with db.conn() as conn:
                    cursor = conn.execute(
                        """
                        SELECT task.task, task.result
                        FROM task
                        JOIN eval ON task.eval_id = eval.run_id
                        WHERE task.result IS NOT NULL
                        AND eval.run_id = ?
                        """,
                        (recorder.run_spec.run_id,),
                    )
                    for row in cursor:
                        task = cached_deserialize(row[0])
                        result = cached_deserialize(row[1])
                        results.append((task, result))

                # Collate the cleanest tasks (aka the last retry idx for each one)
                clean_results = _create_clean_results(results)

                # Retry system errors
                # Look only at clean results to avoid double retries
                for i, (task, result) in enumerate(clean_results):
                    if isinstance(result, ExecutorExceptionWrapper) and isinstance(
                        result.exception, RetryableSystemError
                    ):
                        # Extract the system error by replacing the result
                        clean_results[i] = (task, result.exception)

                        if task.retry_idx < spec.runner.max_retries:
                            new_task = task.model_copy(update={"retry_idx": task.retry_idx + 1})
                            with db.conn() as conn:
                                # ok to do nothing on conflict, it means we already retried this one. no op
                                # TODO(kevinliu) make this more efficient.
                                cursor = conn.execute(
                                    """
                                            INSERT INTO task (eval_id, group_id, task)
                                            VALUES (?, ?, ?)
                                            ON CONFLICT(eval_id, group_id) DO NOTHING
                                            """,
                                    (
                                        recorder.run_spec.run_id,
                                        ".".join(
                                            [
                                                new_task.question_id,
                                                str(new_task.attempt_id),
                                                str(new_task.retry_idx),
                                            ]
                                        ),
                                        dill.dumps(new_task),
                                    ),
                                )
                                conn.commit()
                                row_updated = cursor.rowcount > 0

                            if row_updated:
                                logger.info(
                                    "Requeued task attempt %s with new retry index %d",
                                    f"{new_task.question_id}.{new_task.attempt_id}",
                                    new_task.retry_idx,
                                )
                                logger.warning(
                                    "Task attempt %s failed with error: %s, currently on retry idx %d",
                                    f"{new_task.question_id}.{new_task.attempt_id}",
                                    result.exception,
                                    task.retry_idx,
                                )
                                logger.warning("%s", result.traceback)
                                # VERY IMPORTANT to avoid accidentally finishing early
                                num_tasks += 1

                logger.info(
                    "Currently have N/N results",
                    num_completed=len(results),
                    num_clean=len(clean_results),
                    num_total=num_tasks,
                )
                # Print summary & update progress bar with intermediate metrics
                if (
                    spec.runner.summary_interval
                    and time.monotonic() - last_summary_time > spec.runner.summary_interval
                ):
                    summary = await spec.eval.get_full_summary(clean_results)
                    logger.info("Partial summary: %s", pformat(summary), _print=True)
                    summary["partial"] = True
                    await asyncio.to_thread(recorder.record_final_report, summary)
                    last_summary_time = time.monotonic()

                results_without_system_errors = [
                    (task, result)
                    for task, result in clean_results
                    if not isinstance(result, RetryableSystemError)
                ]

                # Update the progress bar
                pbar.total = num_tasks
                pbar.update(len(results) - pbar.n)
                await spec.eval.update_progress(results_without_system_errors, pbar)

                # Completed all tasks in the db
                if len(results) == num_tasks:
                    break

                await asyncio.sleep(1)

            # We made it!!!
            logger.info("Got back all results!", _print=True)
            summary = await spec.eval.get_full_summary(clean_results)
            logger.info("Got summary")

            await asyncio.to_thread(recorder.record_final_report, summary)

            logger.info(
                f"Summary:\n{pformat(summary)}\nEvaluated {num_tasks} tasks with {spec.eval.get_name()}",
                _print=True,
            )
            logger.info(
                f"\033[36m\033[1mEvalboard Summary: {recorder.evalboard_url('run') or 'unknown, add in pr?'}\033[0m",
                _print=True,
            )
        if spec.runner.enable_slackbot:
            await get_library_config().send_user_notification(
                await _format_slack_message(
                    recorder, spec, start_time, "✅ Eval Complete!", done=True
                ),
                extra=f"```\n{pformat(summary)}\n```",
            )
        return summary
    except (
        # Raised if an exception in this call stack happens
        Exception,
        # Raised if an executor worker crashes; this causes the main process task to get canceled
        # (hence this CancelledError). The real exception is only raised later, by the main process's exit
        # stack which holds the task group running the executor worker, so we cannot catch it here.
        CancelledError,
    ):
        if spec.runner.enable_slackbot:
            await get_library_config().send_user_notification(
                await _format_slack_message(
                    recorder, spec, start_time, "❌ Eval Failed!", done=True
                ),
                extra=f"```\n{traceback.format_exc()}\n```",
            )
        raise


async def run(spec: EvalSpec) -> dict[str, Any]:  # type: ignore
    tasks = list(await spec.eval.get_tasks())
    assert len(tasks) > 0, "No tasks to evaluate"

    if spec.runner.n_tasks is not None:
        tasks = tasks[: spec.runner.n_tasks]

    if spec.runner.shuffle:
        logger.info("Shuffling eval examples...")
        # Shuffle the tasks to avoid any colocation of expensive tasks
        random.shuffle(tasks)

    # Initialize the database if necessary. This will work across two runs.
    if not default_db.get(None):
        # Main process should do backups
        logger.info("Opening database")
        await global_exit_stack.enter_async_context(
            open_run_set_db(backup=spec.runner.should_backup)
        )

    # Build the recorder!
    recorder_config = spec.runner.recorder or get_library_config().get_default_recorder()
    recorder = await recorder_config.factory(spec, len(tasks))

    # Load all tasks into the database
    with db.conn() as conn:
        conn.execute(
            """INSERT INTO eval (run_id, name, start_time, spec, recorder, concurrency) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                recorder.run_spec.run_id,
                spec.eval.get_name(),
                datetime.now(),
                dill.dumps(spec),
                dill.dumps(recorder),
                spec.runner.concurrency if spec.runner.concurrency is not None else 999999,
            ),
        )

        for task in tasks:
            conn.execute(
                """
                INSERT INTO task (eval_id, group_id, task)
                VALUES (?, ?, ?)
                ON CONFLICT(eval_id, group_id) DO NOTHING
                """,
                (
                    recorder.run_spec.run_id,
                    task.question_id + "." + str(task.attempt_id) + "." + str(task.retry_idx),
                    dill.dumps(task),
                ),
            )

        conn.commit()

        logger.info("Eval loaded into database; now running", run_id=recorder.run_spec.run_id)
        return await run_eval_in_database(recorder.run_spec.run_id)


async def validate(spec: EvalSpec) -> dict[str, Any]:
    """
    Dry run, generally without use of a real engine (e.g., with a mock solver).
    Useful to playtest data loading code.
    """

    return await run(
        chz.replace(
            spec,
            runner=chz.replace(spec.runner, recorder=dummy_recorder(), enable_slackbot=False),
        )
    )


__all__ = [
    "run",
    "validate",
    "EvalSpec",
    "RetryableSystemError",
    "Task",
    "RunnerArgs",
    "Eval",
    "run_eval_in_database",
]
