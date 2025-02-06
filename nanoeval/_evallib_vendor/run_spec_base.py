"""
Sorry this file has to exist so we can export nanoeval to contractors, as we can't depend on
evallib_recorder. Unit tests assert that they are equivalent to the evallib_recorder version.
"""

import base64
import dataclasses
import os
from datetime import datetime
from typing import Any, Sequence


def uuid() -> str:
    now = datetime.utcnow()  # noqa: DTZ003
    rand_suffix = base64.b32encode(os.urandom(5)).decode("ascii")
    return now.strftime("%y%m%d%H%M%S") + rand_suffix


@dataclasses.dataclass(kw_only=True)
class RunSpecBase:
    """
    This class represents arbitrary data describing an eval run to be stored in
    Snowflake. You should subclass this class and add any additional fields
    that you want to store in Snowflake.

    To avoid tight coupling, we do not directly import `RunSpec`
    here; however in practice all RunSpecs are currently instances of
    `RunSpec`.

    TODO(kevinliu): This class shouldn't have any properties. Ideally we should
    have evallib's RunSpec inherit from this class and add the properties there.
    """

    model_name: str
    model_names: dict[str, Sequence[str]]
    eval_name: str
    base_eval: str
    split: str
    run_config: Any
    created_by: str
    run_id: str = dataclasses.field(default_factory=uuid)
    run_set_id: str = dataclasses.field(default_factory=uuid)
    created_at: str = dataclasses.field(
        default_factory=lambda: str(datetime.utcnow())  # noqa: DTZ003
    )
    tags: list[str] | None = None
    spec_hash: str | None = None

    def __post_init__(self) -> None:
        if self.__class__ == RunSpecBase:
            raise TypeError(
                f"{RunSpecBase} is an abstract class and should not be instantiated directly."
            )
