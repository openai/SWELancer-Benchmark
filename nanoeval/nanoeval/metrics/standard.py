from typing import Any

import pandas as pd

from nanoeval.library_config import get_library_config


def compute_standard_metrics(
    # (instance, attempt, answer_group_id [int])
    samples_df: pd.DataFrame,
    # (instance, answer_group_id [int], is_correct)
    answer_group_correctness_df: pd.DataFrame,
) -> dict[str, float | str | dict[Any, Any]]:
    return get_library_config().compute_standard_metrics(samples_df, answer_group_correctness_df)


__all__ = ["compute_standard_metrics"]
