import chz
from nanoeval.solvers.computer_tasks.solver import PythonCodingSolver
from nanoeval.asyncio_utils import generator_with_cleanup
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
from typing_extensions import override
from nanoeval.solvers.computer_tasks.steps import FinalResultWithException, Step
from alcatraz.clusters.local import LocalConfig
import shlex

import asyncio
import functools
import os
import re
import subprocess
import threading
import traceback
from contextlib import AsyncExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from textwrap import dedent
from typing import Any, AsyncGenerator, ContextManager, Generator, Generic, TypeVar, cast

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, AsyncGenerator, Generator
from alcatraz.nanoeval_alcatraz.task_to_alcatraz_config import task_to_alcatraz_config
from alcatraz.alcatraz_computer_interface import AlcatrazComputerInterface

from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # This is the default and can be omitted
)


def get_model_response(messages: list[dict[str, Any]]) -> str:
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="gpt-4o",
    )
    return chat_completion.choices[0].message.content


@chz.chz
class SimpleAgentSolver(PythonCodingSolver):
    name: str = "SimpleAgentSolver"
    model: str = "gpt-4o"

    def shortname(self) -> str:
        return "simple-solver"

    @asynccontextmanager
    async def _start_computer(self, task: ComputerTask) -> AsyncGenerator[ComputerInterface, None]:
        # replace with LocalCluster semantics

        alcatraz_env = task_to_alcatraz_config(task, LocalConfig(pull_from_registry=False))

        async with alcatraz_env.build() as cluster:
            yield AlcatrazComputerInterface(cluster_value=cluster)

    @override
    async def run(self, task: ComputerTask) -> AsyncGenerator[Step | FinalResult, None]:
        try:
            async with self._start_computer(task) as computer:
                print(computer)
                # 1. Run the task setup
                await task.setup(computer)

                # 2. Query the API / some agent
                messages = [] 
                for prompt_message in task.prompt:
                    messages.append({
                        "role": "user",
                        "content": str(prompt_message["content"])
                    })
                messages.append({"role": "user", "content": """The repository is cloned in your CWD. You must send Python code in backticks in each response to me, and I will execute the code and send you back the result, for example:
                                                                       
```python
import os
print(os.listdir())
```

You can include other content in your message, as long as it has the Python code block. You must only submit one code block per message.
                                 
The python code block is your means of interactign with the environment; write Python code to view files, edit files, and run commands. Do not leave any steps incomplete. You must implement all fixes yourself.
                                                                       
When you are done, send "DONE" (and nothing else - you don't need a python code block), and we will grade your submission.
                                 
Please note that the Python code is not a Jupyter notebook; you must write a full Python script each time, including imports, and printing things if you want to see the output.
"""})
                max_turns = 30
                print(messages)

                for remaining_turns in range(max_turns, 0, -1):
                    model_response = get_model_response(messages)
                    print(model_response)

                    messages.append({"role": "assistant", "content": model_response})

                    execution_output = None

                    #Check for user-tool calls
                    if "<user-tool>" in model_response:
                        print('User tool called.')
                        await computer.check_shell_command("unzip -q -P 'secretpasswordhere' /app/tests.zip -d /app/tests")
                        execution_output = await computer.send_shell_command("bash -c -i 'user-tool'")
                        print('User tool ran successfully.')
                        execution_output = 'User tool ran successfully, output is in /expensify/user_tool'
                        await computer.send_shell_command(
                            "rm -rf /app/tests"
                        )
                        await computer.send_shell_command("rm -rf /app/tests")
                    else:
                        # Extract Python code from the model response
                        python_blocks = re.findall(r"```python\s*\n(.*?)\n```", model_response, re.DOTALL)

                        if not python_blocks:
                            messages.append({
                                "role": "user",
                                "content": "Warning: No Python code blocks were found in the response. Please include Python code in your replies."
                            })
                            continue

                        code = dedent(python_blocks[0])

                        execution_output = await computer.send_shell_command(f"python -c {shlex.quote(code)}")
                        execution_output = execution_output.output.decode("utf-8", errors="replace")
                        
                    if model_response.lower() == "done":
                        print("Breaking because model is done!")
                        break


                    print(execution_output)

                    # Append the code and its output to the messages
                    messages.append({
                        "role": "user",
                        "content": f"{execution_output}\nTurns left: {remaining_turns - 1}"
                    })

                # 3. Grade and yield the final result
                grade = await task.grade(computer)
                yield FinalResultSuccessful(grade=grade)
        except Exception as e:
            print("Error!")
            raise
            yield FinalResultSuccessful(
                grade=Grade(score=0, grader_log=f"Grading failed with error: {str(e)}")
            )