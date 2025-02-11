import logging
import subprocess

import litecli

import chz
from nanoeval._db import open_run_set_db
from nanoeval.setup import nanoeval_entrypoint

logger = logging.getLogger(__name__)


async def sqlite(run_set_id: str) -> None:
    async with open_run_set_db(backup=False, run_set_id=run_set_id) as db:
        subprocess.check_call([litecli.__name__, str(db.database_file)])


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(sqlite))
