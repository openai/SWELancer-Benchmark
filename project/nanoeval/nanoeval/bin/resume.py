import asyncio
from typing import Any

import structlog.stdlib

import chz
from nanoeval._db import open_run_set_db
from nanoeval.evaluation import run_eval_in_database
from nanoeval.setup import nanoeval_entrypoint

logger = structlog.stdlib.get_logger(component=__name__, _print=True)


async def resume(run_set_id: str, resume_completed_evals: bool = False) -> list[dict[str, Any]]:
    async with open_run_set_db(backup=True, run_set_id=run_set_id) as db:
        with db.conn() as conn:
            # Read out and deserialize all eval specs; then, re run them
            query = """
            SELECT run_id,
                       (SELECT COUNT(*) FROM task WHERE eval_id = eval.run_id AND result IS NOT NULL) AS tasks_done,
                       (SELECT COUNT(*) FROM task WHERE eval_id = eval.run_id) AS total_tasks
                FROM eval
            """
            if not resume_completed_evals:
                query += " WHERE (SELECT COUNT(*) FROM task WHERE eval_id = eval.run_id AND result IS NULL) > 0"
            cursor = conn.execute(query)
            rows = cursor.fetchall()

        logger.info("=" * 80)
        logger.info("Resuming evals")
        logger.info("=" * 80)
        logger.info("Eval specs:")
        for idx, (run_id, tasks_done, total_tasks) in enumerate(rows):
            logger.info(
                "%d. %s (%.1f%% done, %d/%d tasks)",
                idx + 1,
                run_id,
                tasks_done / total_tasks * 100,
                tasks_done,
                total_tasks,
            )

        return await asyncio.gather(*[run_eval_in_database(run_id) for run_id, _, _ in rows])


async def _main(run_set_id: str, resume_completed_evals: bool = False) -> None:
    """
    Resume evals from a previous nanoeval db file.

    Args:
        run_set_id: The ID of the run set to resume.
        resume_completed_evals: Whether to resume evals that have already completed. This is useful if you want to
        recompute summary metrics for an eval that already finished.
    """
    await resume(run_set_id, resume_completed_evals)


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(_main))
