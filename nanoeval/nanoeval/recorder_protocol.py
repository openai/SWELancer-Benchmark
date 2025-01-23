from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, ContextManager, Literal, Protocol, Self

import chz
from nanoeval._evallib_vendor.run_spec_base import RunSpecBase


@dataclass
class RunConfig:
    eval_args: dict[str, Any]
    initial_settings: dict[str, Any]
    max_samples: int
    total_samples: int


@dataclass
class RunSpec(RunSpecBase):
    run_config: RunConfig


class RecorderProtocol(Protocol):
    """
    Minimal interface to the evallib recorder. This is necessary to avoid nanoeval depending on
    any monorepo dependencies. Hopefully for all internal users this is transparent.
    """

    run_spec: Any

    def __enter__(self) -> Self: ...

    def __exit__(self, *args: Any) -> None: ...

    def current_sample_id(self) -> str | None: ...

    def current_group_id(self) -> str | None: ...

    def as_default_recorder(
        self, sample_id: str, group_id: str, **extra: Any
    ) -> ContextManager[None]: ...

    def record_match(
        self,
        correct: bool,
        *,
        expected: Any = None,
        picked: Any = None,
        prob_correct: Any = None,
        **extra: Any,
    ) -> None: ...

    def record_sampling(
        self,
        prompt: Any,
        sampled: Any,
        *,
        extra_allowed_metadata_fields: list[str] | None = None,
        **extra: Any,
    ) -> None: ...

    def record_sample_completed(self, **extra: Any) -> None: ...

    def record_error(self, msg: str, error: Exception | None, **kwargs: Any) -> None: ...

    def record_extra(self, data: Any) -> None: ...

    def record_final_report(self, final_report: Any) -> None: ...

    def evalboard_url(self, view: Literal["run", "monitor"]) -> str | None: ...


@chz.chz
class RecorderConfig:
    """
    Holds configuration for a recorder. You can build the recorder by calling `config.factory(spec)`.

    This layer of indirection + explicitly storing is required because nanoeval needs to use the Snowflake connection
    to make a run set, which is currently not abstracted by `evallib_recorder`. However, we cannot access
    `recorder._conn` directly because:

    - it is private and will change in the future
    - when we make the run set, we haven't built the recorder yet, so we don't have access to the connection!!
    """

    factory: Callable[[RunSpecBase], RecorderProtocol]

    async def log_run_set(self, model_name: str, eval_set_name: str | None) -> str | None:
        """
        Called on every eval. It should mark the eval as part of a "run set" (collection of evals) to a database and return the run set ID.
        """
        return None
