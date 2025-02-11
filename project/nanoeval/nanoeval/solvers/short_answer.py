from __future__ import annotations

import asyncio
import itertools
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from pydantic import BaseModel

import chz
from nanoeval import Eval
from nanoeval.eval import Task
from nanoeval.recorder import get_recorder


class Question(BaseModel):
    question: str
    metadata: dict[str, Any] = {}


class Answer(BaseModel):
    answer: str
    is_correct: bool | None = None
    metadata: dict[str, Any] = {}


class ShortAnswerTask(Task):
    question: Question


@chz.chz
class ShortAnswerSolver(ABC):
    @abstractmethod
    async def solve(self, task: ShortAnswerTask) -> Answer:
        pass


@chz.chz
class MockSolver(ShortAnswerSolver):
    async def solve(self, task: ShortAnswerTask) -> Answer:
        return Answer(answer="dummy")


@chz.chz
class ShortAnswerEval(ABC, Eval[ShortAnswerTask, Answer]):
    """Eval for short answer questions.

    I might add an autograder to this later. Right now, it just samples, and records no metrics.
    """

    solver: ShortAnswerSolver
    samples_per_question: int = 1

    @abstractmethod
    async def _get_tasks(self) -> list[Question]:
        pass

    async def get_tasks(self) -> list[ShortAnswerTask]:
        questions = await self._get_tasks()

        # Manage RNGs
        tasks = []
        for attempt_idx, (q_idx, question) in itertools.product(
            range(self.samples_per_question), enumerate(questions)
        ):
            tasks.append(
                ShortAnswerTask(
                    question=question,
                    question_id=self.get_name() + "." + str(q_idx),
                    attempt_id=attempt_idx,
                )
            )

        return tasks

    async def evaluate(self, task: ShortAnswerTask) -> Answer:
        res = await self.solver.solve(task)
        await asyncio.to_thread(
            get_recorder().record_match,
            correct=False,
            metadata=res.metadata,
        )
        return res

    def process_invalid(self, task: ShortAnswerTask) -> Answer:
        return Answer(answer="dummy", is_correct=False)

    async def get_summary(self, results: list[tuple[ShortAnswerTask, Answer]]) -> dict[str, Any]:
        if not results:
            return {}

        samples_df = pd.DataFrame(
            [
                {
                    "instance": task.question_id,
                    "attempt": task.attempt_id,
                    "correct": answer.is_correct,
                }
                for task, answer in results
            ]
        )
        return {
            "accuracy": samples_df.groupby("instance")["correct"].mean().mean(),
        }
