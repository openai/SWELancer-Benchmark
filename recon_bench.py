import asyncio
import base64
import shlex
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pprint import pformat
from typing import Any, AsyncGenerator, Literal, Sequence, assert_never, cast, get_args
from uuid import uuid4
import ast
import json

from typing import Any
import blobfile as bf
import structlog.stdlib
from openai.types.chat import ChatCompletionMessageParam
from typing_extensions import override
import csv

import chz
from nanoeval.asyncio_utils import generator_with_cleanup
from nanoeval.eval import RetryableSystemError
# from nanoeval.file_utils import writable_root_dir
from nanoeval.solvers.computer_tasks.code_execution_interface import (
    ComputerInterface,
    JupyterComputerInterface,
)
from nanoeval.solvers.computer_tasks.solver import PythonCodingEval, strip_all_metadata
from nanoeval.solvers.computer_tasks.steps import (
    FinalResult,
    FinalResultSuccessful,
    FinalResultWithException,
)
from nanoeval.solvers.computer_tasks.task import ComputerTask, Grade

logger = structlog.stdlib.get_logger(component=__name__, _print=True)

def prompt_chatgpt(info: dict[str, Any]) -> list[ChatCompletionMessageParam]:
    return [
        {
            "role": "user",
            "content": f"You are an expert molecular biologist, tasked with solving the following problem: {info['prompt']}.",
        },
        {
            "role": "user",
            "content": f"You have the following Python package at your disposal: biopython. The documentation for BioPython can be found in the repository, and it has been installed in the python environment. You can create Python files in the /app directory to work on answering the question.",
        },
        {
            "role": "user",
            "content": f"To submit your answer, please create a file called /app/answer.txt (absolute path). You must also create a file called /app/feedback.json (absolute path), where you give feedback in the following format: " + """{'tool_wishlist': 'Explain tools you wish you had / feel that are missing from this environment; or say N/A if you felt the existing tooling was adequate', 'task_issues': 'Explain any problems with the task in your view, e.g. something wasn't accessible in the database, etc. Again, you can state N/A if the task was not broken/invalid.'}""",
        },
        {
            "role": "user",
            "content": f"First, you should read the documentation for biopython. Please only use BioPython; do not use any other libraries that are installed, as they will not be helpful."
        },
    ]

class SWEBenchTask(ComputerTask):
    instance: dict[str, Any]
    retry_message: str = "Keep trying! You did not submit your answer yet; you must submit the final answer in /app/answer.txt and /app/feedback.json. No placeholders are allowed! You must submit to /app directory, not in /data/mnt or anywhere else!"

    cwd: str = "/testbed"
    jupyter_setup: Sequence[str] | None = (
        "bash",
        "-c",
        "conda run -n testbed pip install jupyter && conda run -n testbed jupyter kernel --ip 0.0.0.0",
    )

    @override
    async def _setup(self, computer: ComputerInterface) -> None:
        if isinstance(computer, JupyterComputerInterface):
            await computer.check_execute(
                """import os; assert os.environ.get('CONDA_DEFAULT_ENV') == 'testbed', os.environ.get('CONDA_DEFAULT_ENV')""",
            )
            logger.info("Correct Jupyter environment is loaded.")

    @override
    async def grade(self, computer: ComputerInterface) -> Grade:
        instance_id = self.question_id
        sample_id = f"{self.question_id}.{self.attempt_id}.{self.retry_idx}-{str(uuid4())}"

        logger.info("Grading task...", instance_id=sample_id)

        res = await computer.send_shell_command("cat /app/answer.txt")
        output = res.output.decode("utf-8").strip()

        res_feedback = await computer.send_shell_command("cat /app/feedback.json")
        output_feedback = res_feedback.output.decode("utf-8").strip()

        correct = output == self.instance["answer"]

        return Grade(
            score=1.0 if correct else 0.0,
            grader_log=json.dumps({
                "model_feedback": output_feedback,
                "expected": self.instance["answer"],
                "actual": output
            }),
        )

    @override
    async def check_for_valid_submission(self, computer: ComputerInterface) -> bool:
        res = await computer.send_shell_command("cat /app/answer.txt")
        output = res.output.decode("utf-8").strip()
        print(output)
        return len(output) > 0 and "No such file or directory" not in output

@chz.chz
class SWEBenchEval(PythonCodingEval):
    prompt: str = "chatgpt"

    @override
    def get_name(self) -> str:
        return "SWEBench"

    def _get_tasks(self) -> list[dict]:
        tasks = []
        with open("/Users/samuelgm/Desktop/reconbenchv1p1.csv", "r") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if i == 0:  # second row (first after header) has column descriptions
                    continue
                tasks.append(ast.literal_eval(row['json']))
        return tasks

    @override
    async def get_instances(self) -> list[SWEBenchTask]:
        tasks = self._get_tasks()
        idx = 0
        final_tasks = []
        for bio_data in tasks: 
            prompt = (
                prompt_chatgpt(bio_data)
            )
            docker_image = f"alcatrazswarmcontainers.azurecr.io/biogold_x86:latest"
            final_tasks.append(
                SWEBenchTask(
                    prompt=prompt,
                    question_id=str(idx),
                    attempt_id=0,
                    grade_every_step=False,
                    docker_image=docker_image,
                    cwd="/app",
                    instance=bio_data,
                )
            )
            idx += 1

        print(len(final_tasks))
        return final_tasks[:1]

    @override
    async def evaluate(self, task: ComputerTask) -> FinalResult:
        last_convo = None
        async with generator_with_cleanup(self.solver.run(task)) as gen:
            async for step in gen:
                if step.convo:
                    last_convo = step.convo

                if isinstance(step, (FinalResultSuccessful, FinalResultWithException)):
                    if last_convo:
                        prompt_messages: Any = strip_all_metadata(last_convo)
                    else:
                        prompt_messages = ""

                    if isinstance(step, FinalResultSuccessful):
                        sampled = f"""{step.grade.grader_log}

Finish reasons: {step.finish_status=} {step.max_steps_reached=} {step.max_tokens_reached=} {step.max_time_reached=}
"""
                    elif isinstance(step, FinalResultWithException):
                        sampled = f"\n\n{step.exception}\n\n{step.traceback}"
                    else:
                        assert_never(step)

                    return step

        raise ValueError("Solver did not return a final result! This is a bug.")