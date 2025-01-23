from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from nanoeval.solvers.computer_tasks.steps import FinalResultWithException, Step
from nanoeval.solvers.computer_tasks.task import Grade


@pytest.mark.parametrize(
    "data",
    [
        {
            "schema_version": 0,
            "convo": dict(),
            "correct": False,
            "autograder_result": "",
            "elapsed": timedelta(seconds=1),
        },
        {
            "schema_version": 0,
            "convo": dict(),
            "correct": False,
            "autograder_result": None,
            "elapsed": timedelta(seconds=1),
        },
        # up to date
        {
            "schema_version": 1,
            "convo": dict(),
            "grade": Grade(score=0.0, grader_log=""),
            "elapsed": timedelta(seconds=1),
        },
    ],
)
def test_deserialize_old_step(data: dict[str, Any]) -> None:
    Step.model_validate(data)


def test_final_result_with_exception() -> None:
    FinalResultWithException.from_exception(Exception(), dict())
