from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, ContextManager, Literal, Protocol, Self, runtime_checkable

import chz

# Avoids circular imports
if TYPE_CHECKING:
    from nanoeval.eval import EvalSpec


class RunSpec(Protocol):
    run_id: str
    run_set_id: str


@runtime_checkable
class RecorderProtocol(Protocol):
    """
    Minimal recorder interface.
    """

    run_spec: RunSpec

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


def uuid() -> str:
    now = datetime.utcnow()  # noqa: DTZ003
    rand_suffix = base64.b32encode(os.urandom(5)).decode("ascii")
    return now.strftime("%y%m%d%H%M%S") + rand_suffix


@dataclass
class BasicRunSpec:
    """
    Standard run spec that just holds the run and run set IDs.
    """

    run_id: str
    run_set_id: str


@chz.chz
class RecorderConfig(ABC):
    """
    Holds configuration for a recorder. You can build the recorder by calling `await config.factory(spec)`.
    """

    def _make_default_run_spec(self, spec: EvalSpec) -> BasicRunSpec:
        from nanoeval._db import get_resume_run_set_id

        # TODO(kevinliu) handle run set id
        return BasicRunSpec(
            run_set_id=spec.runner.run_set_id or get_resume_run_set_id(), run_id=uuid()
        )

    @abstractmethod
    async def factory(self, spec: EvalSpec, num_tasks: int) -> RecorderProtocol: ...
