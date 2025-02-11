from __future__ import annotations

import traceback
from abc import ABC
from datetime import timedelta
from typing import Any, ClassVar, Literal

from pydantic import ConfigDict
from pydantic.v1.json import timedelta_isoformat
from typing_extensions import deprecated

from nanoeval.solvers.computer_tasks._versioning import Migration, VersionedModel
from nanoeval.solvers.computer_tasks.task import Grade


def _step_0_to_1(values: dict[str, Any]) -> dict[str, Any]:
    # Migrate correct, autograder_result to new Grade field
    if grader_log := values.pop("autograder_result"):
        values["grade"] = Grade(score=1 if values.pop("correct") else 0, grader_log=grader_log)
    else:
        assert not values.pop("correct")
        values["grade"] = None

    return values


class Step(VersionedModel):
    """
    A single step in the conversation. Contains results from the autograder.

    Extend this class to add more information about the step, e.g. the model's
    output or other metadata you'd like to include in your solver.
    """

    schema_version: int = 1
    _migrations: ClassVar[dict[int, Migration]] = {
        0: _step_0_to_1,
    }

    convo: Any

    # If none, the step wasn't graded.
    grade: Grade | None

    elapsed: timedelta

    type: Literal["step"] = "step"

    @property
    def correct(self) -> bool:
        return self.grade is not None and self.grade.score == 1

    model_config = ConfigDict(json_encoders={timedelta: timedelta_isoformat})


def _final_result_successful_0_to_1(values: dict[str, Any]) -> dict[str, Any]:
    # Migrate correct, autograder_result to new Grade field
    if grader_log := values.pop("grader_log"):
        values["grade"] = Grade(score=1 if values.pop("correct") else 0, grader_log=grader_log)
    else:
        assert not values.pop("correct")
        values["grade"] = None

    return values


class FinalResultBase(ABC, VersionedModel):
    grade: Grade
    convo: Any = None

    @property
    def correct(self) -> bool:  # type: ignore
        return self.grade.score == 1


class FinalResultSuccessful(FinalResultBase):
    finish_status: Literal["finished-successfully"] = "finished-successfully"
    max_steps_reached: bool = False
    max_tokens_reached: bool = False
    max_time_reached: bool = False
    type: Literal["final_result_successful"] = "final_result_successful"

    schema_version: int = 1
    _migrations: ClassVar[dict[int, Migration]] = {
        0: _final_result_successful_0_to_1,
    }


def _final_result_with_exception_0_to_1(values: dict[str, Any]) -> dict[str, Any]:
    # Migrate correct, autograder_result to new Grade field
    values["grade"] = Grade(score=1 if values.pop("correct") else 0, grader_log="")

    return values


class FinalResultWithException(FinalResultBase):
    # How did this episode end? Useful for error tracking.
    finish_status: str

    # The exception that was raised.
    exception: str
    traceback: str

    type: Literal["final_result_exception"] = "final_result_exception"

    @staticmethod
    @deprecated(
        "please use native nanoeval retries using nanoeval.eval.RetryableSystemError instead"
    )
    def from_exception(
        e: BaseException, convo: Any | None, traceback_notes: str = ""
    ) -> "FinalResultWithException":
        finish_status: Literal[
            "error-timeout",
            "error-ace",
            "error-model",
            "error-other",
            "error-user-machine-kernel-unresponsive",
        ]
        exception_name, tb = e.__class__.__name__, traceback.format_exc()
        if "TimeoutError" in exception_name:
            finish_status = "error-timeout"
        elif "SamplingError" in exception_name:
            # Agent sampling error
            finish_status = "error-model"
        elif "AceException" in exception_name:
            finish_status = "error-ace"
        elif "Kernel didn't respond" in tb:
            finish_status = "error-user-machine-kernel-unresponsive"
        else:
            finish_status = "error-other"

        return FinalResultWithException(
            grade=Grade(score=0, grader_log=""),
            finish_status=finish_status,
            exception=exception_name,
            traceback=tb + "\n" + traceback_notes,
            convo=convo,
        )

    # Migration data
    schema_version: int = 1
    _migrations: ClassVar[dict[int, Migration]] = {
        0: _final_result_with_exception_0_to_1,
    }


FinalResult = FinalResultSuccessful | FinalResultWithException
