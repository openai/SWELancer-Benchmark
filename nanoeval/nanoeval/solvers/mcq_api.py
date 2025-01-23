import asyncio
import functools
import logging
import random
import re
from typing import Sequence

import jinja2
import openai
from openai.types.chat import ChatCompletionMessageParam
from typing_extensions import override

import chz
from nanoeval.recorder import get_recorder
from nanoeval.solvers.mcq import Answer, MCQSolver, MCQTask, Question

logger = logging.getLogger(__name__)


MC_PROMPT_FORMAT = """
{{ question }}

{% for letter, answer in letters_to_answers.items() %}
({{ letter }}) {{ answer }}{% endfor %}
""".strip()


@chz.chz
class MCQAPISolver(MCQSolver[Answer]):
    model: str

    @functools.cached_property
    def _client(self):
        return openai.AsyncClient()

    @classmethod
    def _extract_picked_letters(
        cls, sampled: str, answer_keys: set[str], allow_multiple_choices: bool
    ) -> set[str]:
        """
        Extracts the picked letters from the sampled response based on the provided answer keys.

        Args:
            sampled (str): The sampled response text from which to extract the picked letters.
            answer_keys (set): A set containing all possible answer keys (e.g., {"A", "B", "C", "D"}).
            allow_multiple_choices (bool): A flag indicating whether multiple choices are allowed.

        Returns:
            set: A set of picked letters extracted from the sampled response.
        """
        picked_letters = set()
        answer_keys_pattern = "".join(answer_keys)
        single_choice_pattern = re.compile(
            r"Answer[\s\*]*:[\s\*]*[\(\$]*([" + answer_keys_pattern + "])[)$]*"
        )
        multiple_choice_pattern = re.compile(
            r"Answer[\s\*]*:[\s\*]*([" + answer_keys_pattern + r"\s,]*)"
        )

        if allow_multiple_choices:
            match = multiple_choice_pattern.search(sampled)
            if match:
                picked_letters = set(re.findall("[" + answer_keys_pattern + "]", match.group(1)))
        else:
            match = single_choice_pattern.search(sampled)
            if match:
                picked_letters = {match.group(1)}

        return picked_letters.intersection(answer_keys)

    @staticmethod
    def _random_guess(question: Question) -> Answer:
        # choose a random answer
        integer_picked = random.choice(range(len(question.answers)))
        return Answer(
            picked=integer_picked,
            correct=integer_picked in question.correct_indices,
            metadata={
                "random_guess": True,
            },
        )

    @override
    async def solve(self, task: MCQTask) -> Answer:
        question = task.question
        letters_to_answers = {
            chr(ord("A") + i): answer for i, answer in enumerate(question.answers)
        }
        prompt = jinja2.Template(source=MC_PROMPT_FORMAT).render(
            question=task.question.question,
            letters_to_answers=letters_to_answers,
        )
        messages: Sequence[ChatCompletionMessageParam] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Answer the following multiple choice question. The last line of your response should be of the following format: 'Answer: $LETTER' (without quotes) where LETTER is one of {answer_choices}. Think step by step before answering.",
            },
            {"role": "user", "content": prompt},
        ]

        res = await self._client.chat.completions.create(
            messages=messages,
            model=self.model,
        )
        sampled = res.choices[0].message.content
        assert isinstance(sampled, str)

        await asyncio.to_thread(get_recorder().record_sampling, prompt=messages, sampled=res)

        picked_letters = self._extract_picked_letters(
            sampled, set(letters_to_answers.keys()), task.question.allow_multiple_choices
        )

        if not picked_letters:
            logger.warning(
                f"Broken sample. Cannot extract answer and explanation. Message: {sampled}"
            )

        picked = list(picked_letters)[0] if len(picked_letters) == 1 else None
        integer_picked = ord(picked) - ord("A") if picked is not None else -1
        if integer_picked == -1:
            return self._random_guess(task.question)
        return Answer(
            picked=integer_picked,
            correct=integer_picked in question.correct_indices,
            metadata={"correct_format": True},
        )
