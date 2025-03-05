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
from nanoeval_alcatraz.task_to_alcatraz_config import task_to_alcatraz_config
from nanoeval_alcatraz.alcatraz_computer_interface import AlcatrazComputerInterface

from openai import OpenAI
import os
from deepseek_tokenizer import ds_token
from langfuse import Langfuse

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host="http://localhost:3000"
)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)


def count_tokens(messages: list[dict[str, Any]]) -> tuple[int, int]:
    """Count the number of tokens in a list of messages and the last message."""
    total_tokens = 0
    last_message_tokens = 0
    
    for i, message in enumerate(messages):
        # Every message follows format: {"role": role, "content": content}
        message_text = f"{message['role']}\n{message['content']}"
        message_tokens = len(ds_token.encode(message_text))
        
        if i == len(messages) - 1:
            last_message_tokens = message_tokens
        total_tokens += message_tokens
    
    return total_tokens, last_message_tokens

def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str = "deepseek-reasoner") -> float:
    """Calculate the cost of API calls based on token usage."""
    # Pricing per 1K tokens (approximate/example values - adjust as needed)
    MODEL_PRICING = {
        "deepseek-reasoner": {
            "prompt": 0.002,  # $0.002 per 1K tokens
            "completion": 0.002  # $0.002 per 1K tokens
        }
    }
    
    if model not in MODEL_PRICING:
        return 0.0
    
    pricing = MODEL_PRICING[model]
    prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * pricing["completion"]
    
    return prompt_cost + completion_cost

def trim_messages(messages: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
    """Trim messages to fit within token limit by removing older messages."""
    while len(messages) > 1 and count_tokens(messages)[0] > max_tokens:
        messages.pop(1)
    return messages

def get_model_response(model: str, messages: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Get model response and return token usage statistics."""
    messages = trim_messages(messages, 110000)
    
    # Count tokens in the prompt
    prompt_tokens, _ = count_tokens(messages)
    
    combined_messages = []
    for message in messages:
        if message["role"] == "user" and combined_messages and combined_messages[-1]["role"] == "user":
            combined_messages[-1]["content"] += "\n" + message["content"]
        else:
            combined_messages.append(message)
    
    chat_completion = client.chat.completions.create(
        messages=combined_messages,
        model="deepseek-reasoner"
    )

    completion = chat_completion.choices[0].message.content
    completion_tokens = len(ds_token.encode(completion))
    
    usage_info = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": calculate_cost(prompt_tokens, completion_tokens)
    }
    
    return completion, usage_info


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
                # Create a new trace for this task
                trace = langfuse.trace(
                    name=f"SWELancer Task {task.question_id}",
                    metadata={
                        "model": self.model,
                        "solver": self.name,
                    }
                )

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
                                                                       
When you are done, send "DONE" (and nothing else - you don't need a python code block), and we will grade your submission. You should not include "DONE" or attempt to print it in your code. IT should be your very last message after submitting your final solution, on its own.
                                                       
Please note that the Python code is not a Jupyter notebook; you must write a full Python script each time, including imports, and printing things if you want to see the output.
"""})
                max_turns = 30
                print(messages, self.model)

                for remaining_turns in range(max_turns, 0, -1):
                    while True:
                        try:
                           # Create and end generation span
                            generation = langfuse.generation(
                                name="Model Response",
                                model="deepseek-reasoner",
                                model_parameters={
                                    "remaining_turns": remaining_turns,
                                    "total_messages": len(messages)
                                },
                                input=messages,
                                trace_id=trace.id
                            )

                            # Get model response and usage info
                            model_response, usage_info = get_model_response(model=self.model, messages=messages)
                            print(model_response)

                            # Update generation with output and usage info
                            generation.end(
                                output=model_response,
                                usage_details={
                                    "input": usage_info["prompt_tokens"],
                                    "output": usage_info["completion_tokens"],
                                    "cache_read_input_tokens": 0,
                                    "total": usage_info["total_tokens"]
                                },
                                cost_details = {
                                    "input": (0.135 / 1000000) * usage_info["prompt_tokens"],
                                    "cache_read_input_tokens": 0,
                                    "output": (0.550 / 1000000) * usage_info["completion_tokens"],
                                    "total": usage_info["cost"]
                                }
                            )
                            break
                        except Exception as e:
                            print(f"Error: {e}")
                            # Update generation with output and usage info
                            generation.end(
                                output=f"",
                                level="ERROR",
                                status_message = f"Error: {e}"
                            )

                    time.sleep(0.2)
    
                    print(f"Remaining turns: {remaining_turns}")
                    
                    messages.append({"role": "assistant", "content": model_response})

                    execution_output = None

                    #Check for user-tool calls
                    if "<user-tool>" in model_response:
                        print('User tool called.')
                        await computer.check_shell_command("unzip -q -P 'secretpasswordhere' /app/tests.zip -d /app/tests")
                        execution_output = await computer.check_shell_command("bash -c -i 'user-tool'")
                        print('User tool ran, with output:')
                        print(execution_output)
                        execution_output = 'User tool output is in /app/expensify/user_tool'
                        await computer.send_shell_command(
                            "rm -rf /app/tests"
                        )
                        await computer.send_shell_command("rm -rf /app/tests")

                        # Log user tool execution
                        span = langfuse.span(
                            name="User Tool Execution",
                            input="<user-tool>",
                            output=execution_output,
                            metadata={
                                "type": "user_tool",
                                "remaining_turns": remaining_turns
                            },
                            trace_id=trace.id
                        )
                        span.end()
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

                        # Log Python code execution
                        span = langfuse.span(
                            name="Python Code Execution",
                            input=f"```python\n{code}\n```",
                            output=execution_output,
                            metadata={
                                "type": "python_execution",
                                "remaining_turns": remaining_turns
                            },
                            trace_id=trace.id
                        )
                        span.end()
                    
                    print(f"Model response: '{model_response}'   | '{model_response.lower()}'")
                    if model_response.lower().endswith("done"):
                        print("Breaking because model is done!")
                        break

                    print(execution_output)
                    if execution_output.lower().strip().endswith("done"):
                        print("Breaking because execution is done!")
                        break

                    # Append the code and its output to the messages
                    messages.append({
                        "role": "user",
                        "content": f"{execution_output}\nTurns left: {remaining_turns - 1}"
                    })

                # 3. Grade and yield the final result
                grade = await task.grade(computer)

                # Log the final score
                langfuse.score(
                     name="Task Grade",
                     value=grade.score,
                     comment=grade.grader_log,
                     trace_id=trace.id
                )

                # End the trace
                #trace.end()
                
                # Ensure all events are sent
                langfuse.flush()

                yield FinalResultSuccessful(grade=grade)
        except Exception as e:
            print(f"Error: {e}")
            langfuse.score(
                name="Task Grade",
                value=0,
                comment=f"Grading failed with error: {str(e)}",
                trace_id=trace.id
            )

            raise
            yield FinalResultSuccessful(
                grade=Grade(score=0, grader_log=f"Grading failed with error: {str(e)}")
            )