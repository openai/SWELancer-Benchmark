import logging

import chz
from nanoeval._db import open_run_set_db
from nanoeval.setup import nanoeval_entrypoint

logger = logging.getLogger(__name__)


async def concurrency(run_set_id: str, set: int) -> None:
    async with open_run_set_db(backup=False, run_set_id=run_set_id) as db:
        with db.conn() as conn:
            # Read out and deserialize all eval specs; then, re run them
            prev_concurrency = int(
                conn.execute(
                    """
                select value from metadata where key = 'max_concurrency'
                """
                ).fetchone()[0]
            )
            logger.info("Previous concurrency: %d", prev_concurrency)

            # Update it
            conn.execute(
                """
                update metadata set value = ? where key = 'max_concurrency'
                """,
                (set,),
            )
            logger.info("New concurrency: %d", set)
            conn.commit()


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(concurrency))
