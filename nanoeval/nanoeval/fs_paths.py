"""
This file describes where nanoeval and its components save state in the filesystem.
"""

from __future__ import annotations

import functools
from pathlib import Path

from nanoeval.library_config import get_library_config, root_dir


def get_package_root() -> Path:
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent

    if current_dir.name != "nanoeval" or parent_dir.name != "nanoeval":
        raise ValueError("Couldn't find the root of the `nanoeval` module!")

    return parent_dir


@functools.cache
def writable_root_dir() -> str:
    return get_library_config().writable_root_dir()


# The folder where databases are saved.
@functools.cache
def database_dir() -> Path:
    path = root_dir()
    path.mkdir(exist_ok=True, parents=True)
    return path


# The folder where we save stack traces from executors.
@functools.cache
def stacktrace_root_dir() -> Path:
    path = root_dir() / "stack_traces"
    path.mkdir(exist_ok=True, parents=True)
    return path
