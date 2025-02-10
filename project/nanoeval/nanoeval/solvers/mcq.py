from __future__ import annotations

import asyncio
import itertools
import random
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generic, Self, TypeVar

import numpy as np
import pandas as pd
from pydantic import BaseModel, model_validator
from typing_extensions import override

import chz
from nanoeval.asyncio_utils import HasAsyncContextManager
from nanoeval.evaluation import Eval, Task
from nanoeval.metrics.standard import compute_default_metrics
from nanoeval.recorder import get_recorder


class Question(BaseModel):
    question: str
    answers: list[str]
    correct_indices: set[int]
    # This allows solver to use randomness (e.g. randomizing over prompts) in a
    # reproducible way. If None, the solver should be deterministic.
    image: str | None = None  # solver code assumes image is in base64 encoding
    seed: int | None = 42

    # Whether the question may have multiple correct answers.
    # If True, the solver should return a set of picked indices, which must match correct_indices to be marked correct.
    # If False, the solver should return a single picked index, which must be in correct_indices to be marked correct.
    allow_multiple_choices: bool = False

    @model_validator(mode="after")
    def validate_correct_indices(self) -> Self:
        answers, correct_indices = self.answers, self.correct_indices
        assert answers is not None and correct_indices is not None
        if not all(0 <= i < len(answers) for i in correct_indices):
            raise ValueError(
                "Each element of correct_indices must be within the range of the answers list."
            )
        return self


class Answer(BaseModel):
    correct: bool

    # Use an int when there is only one correct answer, and a set when there are multiple.
    picked: int | set[int]
    metadata: dict[str, Any] = {}


class MCQTask(Task):
    question: Question


TAnswer = TypeVar("TAnswer", bound=Answer)


@chz.chz
class MCQSolver(Generic[TAnswer], ABC, HasAsyncContextManager):
    @abstractmethod
    async def solve(self, task: MCQTask) -> TAnswer:
        pass

    def compute_extra_metrics(
        self, results: list[tuple[MCQTask, TAnswer]], n_consensus: int
    ) -> dict[str, Any]:
        del results
        return {}


@chz.chz
class MockSolver(MCQSolver[Answer]):
    @override
    async def solve(self, task: MCQTask) -> Answer:
        if task.question.allow_multiple_choices:
            if random.random() > 0.5:
                # Choose the correct indices as the answer
                answer = task.question.correct_indices
            else:
                # Choose a random set of indices
                answer = set(
                    random.sample(
                        range(len(task.question.answers)),
                        random.randint(1, len(task.question.answers)),
                    )
                )
            return Answer(
                picked=answer,
                correct=answer == task.question.correct_indices,
            )
        else:
            if random.random() > 0.5:
                # Choose a random correct index
                answer = random.choice(list(task.question.correct_indices))  # type: ignore
            else:
                answer = random.choice(range(len(task.question.answers)))  # type: ignore

            assert isinstance(answer, int)
            return Answer(picked=answer, correct=answer in task.question.correct_indices)


@chz.chz
class MCQEval(ABC, Eval[MCQTask, Answer]):
    solver: MCQSolver[Any]
    n_consensus: int = 1

    @override
    @asynccontextmanager
    async def _context(self) -> AsyncGenerator[None, None]:
        async with self.solver:
            yield

    @abstractmethod
    async def _get_tasks(self) -> list[Question]:
        pass

    async def get_tasks(self) -> list[MCQTask]:
        questions = await self._get_tasks()

        tasks = []
        for attempt_idx, (q_idx, question) in itertools.product(
            range(self.n_consensus), enumerate(questions)
        ):
            tasks.append(
                MCQTask(
                    question=question,
                    question_id=self.get_name() + "." + str(q_idx),
                    attempt_id=attempt_idx,
                )
            )

        return tasks

    @override
    async def update_progress(
        self, partial_results: list[tuple[MCQTask, Answer]], pbar: Any
    ) -> None:
        acc = np.mean([result.correct for _, result in partial_results])  # type: ignore
        pbar.set_postfix(acc=acc)

    async def evaluate(self, task: MCQTask) -> Answer:
        res = await self.solver.solve(task)

        if task.question.allow_multiple_choices:
            assert isinstance(res.picked, set)
            if len(res.picked) == 1:
                # make formatting match the evallib recorder for `expected`
                # meaning that if picked is a list with one element, we should return that element
                picked: Any = list(res.picked)[0]
            else:
                picked = list(res.picked)
        else:
            picked = res.picked

        await asyncio.to_thread(
            get_recorder().record_match,
            correct=res.correct,
            picked=picked,
            expected=list(task.question.correct_indices),
            metadata=res.metadata,
        )

        return res

    async def get_summary(self, results: list[tuple[MCQTask, Answer]]) -> dict[str, Any]:
        """
        instance_to_answer_group_ids maps each instance key to a np array where each element
        in the array corresponds to a sample. The value of that element is a unique int index
        corresponding to the unique "group" of answers that the sample was grouped into
        for consensus. We typically group samples based on exact string matching of
        their normalized answers.

        instance_to_group_correctness maps each instance key to a np array of type bool
        where each element of the array corresponds to an answer group. The value of that
        bool is whether the answers that fell in that group were correct or not.
        """

        if not results:
            return {}

        # Validate format
        for task, result in results:
            if task.question.allow_multiple_choices:
                assert isinstance(result.picked, set)
                assert all(isinstance(p, int) for p in result.picked)
            else:
                assert isinstance(result.picked, int)

        def _choice_to_answer_group(picked: int | set[int]) -> int:
            if isinstance(picked, set):
                assert all(p < 10 for p in picked)
                # Every answer group is a unique power of 10
                return sum([10 ** (i + 1) + p for i, p in enumerate(picked)])
            return picked

        samples_df = pd.DataFrame(
            [
                {
                    "instance": task.question_id,
                    "attempt": task.attempt_id,
                    "answer_group_id": _choice_to_answer_group(answer.picked),
                }
                for task, answer in results
            ]
        )
        answer_group_correctness_df = pd.DataFrame(
            [
                {
                    "instance": task.question_id,
                    "answer_group_id": _choice_to_answer_group(answer.picked),
                    "is_correct": answer.correct,
                }
                for task, answer in results
            ]
        ).drop_duplicates(["instance", "answer_group_id"])

        return {
            **(
                await asyncio.to_thread(
                    compute_default_metrics, samples_df, answer_group_correctness_df
                )
            ),
            **(
                await asyncio.to_thread(
                    self.solver.compute_extra_metrics, results, n_consensus=self.n_consensus
                )
            ),
        }
