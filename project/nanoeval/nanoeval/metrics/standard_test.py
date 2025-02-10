import math
from typing import Any, cast

import pandas as pd
import pytest

from nanoeval.metrics.standard import (
    compute_default_metrics,
    compute_default_metrics_on_correctness_without_answer_groups,
)


def test_metrics_handle_ragged_results() -> None:
    """
    Metrics calculator should weight instances equally regardless of each number of attempts.
    """
    metrics = compute_default_metrics(
        pd.DataFrame(
            [
                {
                    "instance": "a",
                    "attempt": 0,
                    "answer_group_id": 0,
                },
                {
                    "instance": "a",
                    "attempt": 1,
                    "answer_group_id": 0,
                },
                {
                    "instance": "b",
                    "attempt": 0,
                    "answer_group_id": 1,
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    "instance": "a",
                    "answer_group_id": 0,
                    "is_correct": True,
                },
                {
                    "instance": "b",
                    "answer_group_id": 1,
                    "is_correct": False,
                },
            ]
        ),
    )
    assert math.isclose(cast(float, metrics["accuracy"]), 0.5)


@pytest.mark.parametrize(
    "data, expected",
    [
        # Simple
        (
            [
                {
                    "instance": "a",
                    "attempt": 0,
                    "is_correct": True,
                },
                {
                    "instance": "b",
                    "attempt": 0,
                    "is_correct": False,
                },
            ],
            {"accuracy": 0.5},
        ),
        # 2/3
        (
            [
                {
                    "instance": "a",
                    "attempt": 0,
                    "is_correct": True,
                },
                {
                    "instance": "b",
                    "attempt": 0,
                    "is_correct": False,
                },
                {
                    "instance": "c",
                    "attempt": 0,
                    "is_correct": True,
                },
            ],
            {"accuracy": 2 / 3},
        ),
        # Ragged results
        (
            [
                {
                    "instance": "a",
                    "attempt": 0,
                    "is_correct": True,
                },
                {
                    "instance": "a",
                    "attempt": 1,
                    "is_correct": False,
                },
                {
                    "instance": "c",
                    "attempt": 0,
                    "is_correct": True,
                },
                {
                    "instance": "c",
                    "attempt": 1,
                    "is_correct": True,
                },
                {
                    "instance": "c",
                    "attempt": 2,
                    "is_correct": True,
                },
            ],
            {"accuracy": (1 / 2 + 3 / 3) / 2},
        ),
        # Empty case
        ([], {}),
    ],
)
def test_compute_metrics_on_correctness_without_answer_groups(
    data: list[dict[str, Any]], expected: dict[str, float]
) -> None:
    metrics = compute_default_metrics_on_correctness_without_answer_groups(pd.DataFrame(data))
    for key, value in expected.items():
        assert math.isclose(cast(float, metrics[key]), value)
