from __future__ import annotations

from typing import Any

import numpy as np
import pytest

import chz
from nanoeval.solvers.mcq import Answer, MCQEval, MCQSolver, MCQTask, Question


# Dummy solver to satisfy abstract class instantiation
@chz.chz
class DummySolver(MCQSolver[Answer]):
    async def solve(self, task: MCQTask) -> Answer:  # type: ignore
        pass  # Not used in tests


# Concrete MCQEval class for testing
@chz.chz
class ConcreteMCQEval(MCQEval):
    async def _get_tasks(self) -> list[Question]:  # type: ignore
        pass  # Not used in tests


@pytest.mark.asyncio
async def test_single_correct_answer() -> None:
    question = Question(
        question="What is 2+2?",
        answers=["3", "4"],
        correct_indices={1},
        allow_multiple_choices=False,
    )
    task = MCQTask(question=question, question_id="id1")
    answer = Answer(picked=1, correct=True)
    eval_instance = ConcreteMCQEval(solver=DummySolver())
    results: list[Any] = [(task, answer)]
    summary = await eval_instance.get_full_summary(results)
    assert summary["accuracy"] == 1.0
    assert summary["metrics_including_errors"]["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_multiple_correct_answers_fail() -> None:
    question = Question(
        question="Select prime numbers",
        answers=["2", "3", "4", "5"],
        correct_indices={0, 1, 3},
        allow_multiple_choices=True,
    )
    task = MCQTask(question=question, question_id="id1")

    # wrong -- picked must be a set
    answers = [Answer(picked=i, correct=(i in task.question.correct_indices)) for i in [0, 1, 3]]
    results: list[Any] = [(task, answer) for answer in answers]
    eval_instance = ConcreteMCQEval(solver=DummySolver())
    with pytest.raises(AssertionError):
        await eval_instance.get_full_summary(results)


@pytest.mark.asyncio
async def test_multiple_correct_answers() -> None:
    question = Question(
        question="Select prime numbers",
        answers=["2", "3", "4", "5"],
        correct_indices={0, 1, 3},
        allow_multiple_choices=True,
    )
    task = MCQTask(question=question, question_id="id1")
    answers = [Answer(picked=task.question.correct_indices, correct=True)]
    results: list[Any] = [(task, answer) for answer in answers]
    eval_instance = ConcreteMCQEval(solver=DummySolver())
    summary = await eval_instance.get_full_summary(results)
    assert summary["accuracy"] == 1.0
    assert np.isclose(summary["metrics_including_errors"]["accuracy"], 1.0)


@pytest.mark.asyncio
async def test_incorrect_answers() -> None:
    question = Question(
        question="What is the capital of France?",
        answers=["Paris", "London"],
        correct_indices={0},
        allow_multiple_choices=False,
    )
    task = MCQTask(question=question, question_id="id1")
    answers = [Answer(picked=1, correct=False)]
    results: list[Any] = [(task, answer) for answer in answers]
    eval_instance = ConcreteMCQEval(solver=DummySolver())
    summary = await eval_instance.get_full_summary(results)
    assert summary["accuracy"] == 0.0
    assert np.isclose(summary["metrics_including_errors"]["accuracy"], 0.0)


@pytest.mark.asyncio
async def test_mixed_answers() -> None:
    question = Question(
        question="Select even numbers",
        answers=["1", "2", "3", "4"],
        correct_indices={1, 3},
        allow_multiple_choices=True,
    )
    task = MCQTask(question=question, question_id="id1")
    answers = [
        Answer(picked={1, 3}, correct=True),
        Answer(picked={0, 1}, correct=False),
        Answer(picked={1}, correct=False),
        Answer(picked={1, 3}, correct=True),
        Answer(picked={1, 3}, correct=True),
        Answer(picked={1}, correct=False),
        Answer(picked={1}, correct=False),
        Answer(picked={1, 4}, correct=False),
        Answer(picked={1}, correct=False),
        Answer(picked={1}, correct=False),
    ]
    results: list[Any] = [(task, answer) for answer in answers]
    eval_instance = ConcreteMCQEval(solver=DummySolver())
    summary = await eval_instance.get_full_summary(results)
    assert np.isclose(summary["accuracy"], 3 / 10)
    assert np.isclose(summary["metrics_including_errors"]["accuracy"], 3 / 10)
