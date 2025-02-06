from __future__ import annotations

import random

import blobfile as bf
import pandas as pd
from typing_extensions import override

import chz
from nanoeval.solvers.mcq import MCQEval, Question


@chz.chz
class GPQAEval(MCQEval):
    """
    Note: PLEASE do not use this as a canonical implementation of GPQA. It is
    designed to be a demo of nanoeval but may not be the best way to run GPQA.
    """

    data_file: str = "https://openaipublic.blob.core.windows.net/simple-evals/gpqa_diamond.csv"

    @override
    def get_name(self) -> str:
        return "GPQA_diamond_not_canonical"

    @override
    async def _get_tasks(self) -> list[Question]:
        with bf.BlobFile(self.data_file, "r") as f:
            df = pd.read_csv(f)

        samples = []
        for _index, row in df.iterrows():
            list_choices = [
                row["Incorrect Answer 1"],
                row["Incorrect Answer 2"],
                row["Incorrect Answer 3"],
                row["Correct Answer"],
            ]

            random.shuffle(list_choices)
            samples.append(
                Question(
                    question=row.Question,
                    answers=list_choices,
                    correct_indices={list_choices.index(row["Correct Answer"])},
                )
            )

        return samples
