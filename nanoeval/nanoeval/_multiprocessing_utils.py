from __future__ import annotations

import functools
import logging
import multiprocessing
import threading
from typing import Any, cast

import dill
import loky
from loky import get_reusable_executor, set_loky_pickler
from loky.backend import reduction
from loky.backend.context import set_start_method

from nanoeval.setup import global_exit_stack

logger = logging.getLogger(__name__)


@functools.cache
def _set_loky_parameters() -> None:
    # This function must be cached because loky doesn't like when you set the start
    # method twice.

    # I think the default causes SIGALRM termination
    # errors when using `nanoeval.extras.watcher`.
    # https://go/think/?sample_id=7c381fa15bab4f268848add164510072
    set_start_method("spawn")
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        # "context has already been set"
        pass
    # We use loky+dill because they can pickle much more than cPickle (e.g. lambdas).
    set_loky_pickler("dill")


def check_multiprocess_safe(obj: Any) -> None:
    """
    Check if an object is safe for multiprocessing. This is used in validations so
    that we can catch errors early, before we initialize a ProcessPoolExecutor and
    actually send the object through.
    """
    _set_loky_parameters()

    try:
        # Try doing loky dump.
        reduction.loads(reduction.dumps(obj))
    except (dill.PicklingError, TypeError) as e:
        raise ValueError(
            f"Object {obj} is not pickleable, it will not work with multiprocessing.\n"
            "If you are getting this error (particularly with unpickleable ContextVar), try making sure no pickled objects are in __main__; run your eval from a different module! See https://stackoverflow.com/questions/73584583/importerror-for-top-level-package-when-trying-to-use-dill-to-pickle-entire-packa for more information."
        ) from e


@functools.cache
def multiprocess_stop_signal() -> threading.Event:
    return multiprocessing.get_context("spawn").Manager().Event()


_executor_cache: loky.Executor | None = None


def _shutdown() -> None:
    global _executor_cache
    if _executor_cache is not None:
        # Set the stop signal to stop all child processes.
        multiprocess_stop_signal().set()

        # Wait for all child processes to terminate.
        logger.info(
            "Waiting for all child processes to terminate (sent stop signal, if the script hangs here, CTRL+C to force exit. You might need to manually kill child processes)..."
        )
        _executor_cache.shutdown(wait=True)
        _executor_cache = None


def get_loky_executor(num_processes: int | None = None) -> loky.Executor:
    global _executor_cache
    _set_loky_parameters()

    if _executor_cache is None:
        _executor_cache = get_reusable_executor(
            # Always reuse, even if flags change
            reuse=cast(Any, True),
            max_workers=num_processes,
            # Some eval code...
            # creates new processes. These don't seem to get cleaned up properly
            # when loky closes idle executors, probably because we don't use
            # hard_exit. Because of this, it seems like a deadlock can happen
            # where:
            #
            # 1. Loky requests termination of the executor due to idle timeout
            # 2. The executor waits on its subprocesses, due to default code in
            #    multiprocessing.
            # 3. The subprocesses are waiting to get terminated by the atexit handler
            #    in the executor. However, we never get to atexit because multiprocessing
            #    closes subprocesses before calling atexit.
            #
            # For example, see this executor traceback:
            #
            # Process 73472: /root/.pyenv/versions/3.11.8/bin/python3 -c from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=23, pipe_handle=41) --multiprocessing-fork
            # Python v3.11.8 (/root/.pyenv/versions/3.11.8/bin/python3.11)
            #
            # Thread 73472 (idle): "MainThread"
            #     select (selectors.py:415)
            #     wait (multiprocessing/connection.py:947)
            #     poll (multiprocessing/popen_forkserver.py:65)
            #     wait (multiprocessing/popen_fork.py:43)
            #     join (multiprocessing/process.py:149)
            #     _exit_function (multiprocessing/util.py:360) # <--- waiting for all subprocesses to exit, doesn't realize they're waiting for it
            #     _bootstrap (multiprocessing/process.py:317)
            #     _main (multiprocessing/spawn.py:135)
            #     spawn_main (multiprocessing/spawn.py:122)
            #     <module> (<string>:1)
            #
            # This causes it to block the queue of actual executors that want to
            # return results. This commit fixes the issue by simply not ever
            # closing executors. By not closing the executors, we can essentially
            # sidestep the deadlock on close issue and finish the eval successfully.
            timeout=1_000_000,
        )

        global_exit_stack.callback(_shutdown)

    return _executor_cache
