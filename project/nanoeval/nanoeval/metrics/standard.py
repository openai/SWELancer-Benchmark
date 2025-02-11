from __future__ import annotations

from typing import Any, Awaitable, Callable, Sequence, cast

import pandas as pd
from more_itertools import flatten

from nanoeval.eval import RetryableSystemError, TResult, TTask
from nanoeval.library_config import get_library_config


def _validate_input_data(
    samples_df: pd.DataFrame, answer_group_correctness_df: pd.DataFrame
) -> None:
    # Ensure 'samples_df' has the required columns
    required_sample_columns = {"instance", "attempt", "answer_group_id"}
    if not required_sample_columns.issubset(samples_df.columns):
        missing_cols = required_sample_columns - set(samples_df.columns)
        raise ValueError(f"'samples_df' is missing required columns: {missing_cols}")

    assert (
        samples_df["instance"].str.contains(":").sum() == 0
    ), "Instance names cannot contain ':' (used in bootstrapping)"

    # Ensure 'answer_group_correctness_df' has the required columns
    required_correctness_columns = {"instance", "answer_group_id", "is_correct"}
    if not required_correctness_columns.issubset(answer_group_correctness_df.columns):
        missing_cols = required_correctness_columns - set(answer_group_correctness_df.columns)
        raise ValueError(
            f"'answer_group_correctness_df' is missing required columns: {missing_cols}"
        )

    # Ensure that every (instance, answer_group_id) pair in 'samples_df' is present in 'answer_group_correctness_df'
    missing_pairs = samples_df[["instance", "answer_group_id"]].merge(
        answer_group_correctness_df,
        on=["instance", "answer_group_id"],
        how="left",
    )
    missing_pairs = missing_pairs[missing_pairs["is_correct"].isnull()]
    if not missing_pairs.empty:
        raise ValueError(
            f"The following (instance, answer_group_id) pairs are missing from 'answer_group_correctness_df': {missing_pairs}"
        )


def compute_default_metrics(
    # (instance, attempt, answer_group_id [int])
    samples_df: pd.DataFrame,
    # (instance, answer_group_id [int], is_correct)
    answer_group_correctness_df: pd.DataFrame,
) -> dict[str, float | str | dict[Any, Any]]:
    """
    Compute standard metrics (pass, cons, etc.) for evals that can measure correctness at the level of answer groups (e.g., a multiple choice question for which one or more answers are correct).

    answer_group: an integer representing a group of answers that are considered equivalent. For example, all A answers
    for a given question.
    """

    _validate_input_data(samples_df, answer_group_correctness_df)

    return get_library_config().compute_default_metrics(samples_df, answer_group_correctness_df)


def compute_default_metrics_on_correctness_without_answer_groups(
    # (instance [str], attempt [int], is_correct)
    correctness_df: pd.DataFrame,
) -> dict[str, float | str | dict[Any, Any]]:
    """
    Compute metrics for "simple" sets of evals that have a simple binary is_correct field rather than
    answer groups (for example, did a particular programming problem pass the unit tests?).

    Simple helper function around compute_default_metrics.
    """

    if correctness_df.empty:
        return {}

    samples_df = correctness_df.copy()
    samples_df["answer_group_id"] = samples_df["is_correct"].astype(int)
    del samples_df["is_correct"]

    # Create two answer groups: 0 is wrong, 1 is right.
    answer_group_correctness_df = pd.DataFrame(
        flatten(
            [
                {
                    "instance": sample.instance,
                    "answer_group_id": 0,
                    "is_correct": False,
                },
                {
                    "instance": sample.instance,
                    "answer_group_id": 1,
                    "is_correct": True,
                },
            ]
            for sample in samples_df.itertuples()
        )
    )

    return compute_default_metrics(samples_df, answer_group_correctness_df)


async def handle_system_errors_and_compute_metrics(
    metrics_fn: Callable[[list[tuple[TTask, TResult]]], Awaitable[dict[str, Any]]],
    results: Sequence[tuple[TTask, TResult | RetryableSystemError]],
    process_invalid: Callable[[TTask], TResult],
) -> dict[str, Any]:
    """
    Computes two sets of metrics. The first (top level) set of metrics is computed by
    EXCLUDING rollouts that terminated in system errors. The second (nested) set of metrics
    is computed by treating system errors as failures (a pessimistic lower bound of the
    accuracy).

    Note that it is sometimes not possible to have *valid* metrics when you exclude the system
    errors. This is for two reasons:

    1. Suppose you run with 16 rollouts per instance and want to calculate pass@16, but one of
       the rollouts fails. If you exclude it, you fundamentally don't have enough information
       to calculate pass@16 anymore.
    2. Sometimes all samples for a given instance may fail, which means excluding all of them
       excludes the instance entirely from metrics. This means you effectively are evaluating
       on an arbitrary subset of the dataset, which is not valid.

    Due to these issues, we return a boolean `is_valid` field in the top level metrics that indicates
    if the metrics are valid or not. We also only report `metric@k` metrics when we actually got >= k
    rollouts for every instance (otherwise it reports an error in a string).

    The `metrics_including_errors` field does not suffer from the caveats above, but it is a
    pessimistic lower bound of the accuracy that may be affected by things other than the capability
    of the model under test (i.e., any system errors).
    """

    def _process_invalid_or_none(task: TTask) -> TResult | None:
        try:
            return process_invalid(task)
        except NotImplementedError:
            return None

    results_treating_system_errors_as_fails = [
        (
            task,
            _process_invalid_or_none(task) if isinstance(result, RetryableSystemError) else result,
        )
        for task, result in results
    ]
    task_ids_including_errors = {
        task.question_id for task, _ in results_treating_system_errors_as_fails
    }

    results_excluding_errors = [
        (task, result) for task, result in results if not isinstance(result, RetryableSystemError)
    ]
    task_ids_excluding_errors = {task.question_id for task, _ in results_excluding_errors}

    summary = {
        **(await metrics_fn(results_excluding_errors)),
        "is_valid": len(task_ids_including_errors) == len(task_ids_excluding_errors),
        "num_tasks": len(task_ids_excluding_errors),
    }

    if not any(r is None for _, r in results_treating_system_errors_as_fails):
        # results are well defined
        assert len(task_ids_excluding_errors) <= len(task_ids_including_errors)

        summary |= {
            "metrics_including_errors": {
                **(await metrics_fn(cast(Any, results_treating_system_errors_as_fails))),
                "num_tasks": len(task_ids_including_errors),
            }
        }

    return summary
