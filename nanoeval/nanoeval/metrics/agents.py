from __future__ import annotations

from typing import Any

import pandas as pd

from nanoeval.eval import RetryableSystemError, Task
from nanoeval.metrics.standard import compute_standard_metrics


def _compute_metrics_plus_outcome_aggregations(samples_df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute standard metrics and aggregations for a given DataFrame of samples.
    """

    # Get answer_group_id on samples_df
    samples_df["answer_group_id"] = samples_df.groupby("instance").cumcount()
    answer_group_correctness_df = samples_df[["instance", "attempt", "answer_group_id"]]
    answer_group_correctness_df["is_correct"] = samples_df["correct"]

    metrics: dict[str, Any] = {
        **compute_standard_metrics(samples_df, answer_group_correctness_df),
        "aggregations": {
            "num_tasks": len(samples_df["instance"].unique()),
            "num_attempts": len(samples_df),
            "num_correct": int(samples_df["correct"].sum()),
            "num_incorrect": int((~samples_df["system_error"] & ~samples_df["correct"]).sum()),
            "num_system_error": int(samples_df["system_error"].sum()),
            "error_breakdown": samples_df[samples_df["error"].notnull()]["error"]
            .value_counts()
            .to_dict(),
        },
    }

    # Validations
    assert metrics["aggregations"]["num_correct"] + metrics["aggregations"][
        "num_incorrect"
    ] + metrics["aggregations"]["num_system_error"] == len(samples_df), f"{metrics=}, {samples_df=}"
    assert (
        sum(metrics["aggregations"]["error_breakdown"].values())
        == metrics["aggregations"]["num_system_error"]
    )

    return metrics


def get_summary_error_aware(
    results: list[tuple[Task, bool | RetryableSystemError]],
) -> dict[str, Any]:
    """
    Reusable utility function that computes a summary including a bunch of metadata about
    an agent rollout. Primary metrics of interest are pass@k, mlpr@k. cons@k is broken here
    and should be ignored, as we don't have a typical way to group rollouts.

    Correctly handles tasks that failed with a system error by not including them in top-level
    metrics. Instead, they are included in the "metrics_including_errors" field.
    """

    if not results:
        return {}

    samples_df = pd.DataFrame(
        {
            "instance": [task.question_id for task, _ in results],
            "attempt": [task.attempt_id for task, _ in results],
            "correct": [
                not isinstance(result, RetryableSystemError) and result for _, result in results
            ],
            "system_error": [isinstance(result, RetryableSystemError) for _, result in results],
            "error": [
                str(result) if isinstance(result, RetryableSystemError) else None
                for (_, result) in results
            ],
        }
    )
    errored_tasks = set(samples_df[samples_df["system_error"]]["instance"])
    non_errored_tasks = set(samples_df[~samples_df["system_error"]]["instance"])
    missing_tasks = list(errored_tasks - non_errored_tasks)
    summary: dict[str, Any] = {
        # The standard metrics are computed excluding errored samples. This means they may
        # lack some tasks if all attempts of that task errored. If this happens, we still
        # report all metrics but consider the results invalid.
        **_compute_metrics_plus_outcome_aggregations(
            samples_df[~samples_df["system_error"]].reindex(columns=samples_df.columns),
        ),
        # The metrics including errors include all errors.
        "metrics_including_errors": _compute_metrics_plus_outcome_aggregations(samples_df),
        "missing_tasks": missing_tasks,
    }

    # Results are considered "valid" if num_tasks == metrics_including_errors["num_tasks"]
    summary["is_valid"] = summary["num_tasks"] == summary["metrics_including_errors"]["num_tasks"]
    assert summary["is_valid"] == (len(missing_tasks) == 0)

    return summary
