import logging
import subprocess

import chz
from nanoeval._db import open_run_set_db
from nanoeval.setup import nanoeval_entrypoint

logger = logging.getLogger(__name__)


async def sqlite(run_set_id: str) -> None:
    # If sqlite3 isn't installed, install it
    try:
        subprocess.check_call(
            ["which", "sqlite3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        subprocess.check_call(["sudo", "apt-get", "install", "sqlite3"])

    async with open_run_set_db(backup=False, run_set_id=run_set_id) as db:
        subprocess.check_call(["sqlite3", str(db.database_file)])


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(sqlite))
