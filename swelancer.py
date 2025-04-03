import asyncio
import json
import ast
import re
import os
from typing import Any, Literal, Sequence, assert_never, get_args
from typing_extensions import TypedDict

from uuid import uuid4

import structlog.stdlib
from openai.types.chat import ChatCompletionMessageParam
from typing_extensions import override
from nanoeval.eval import RetryableSystemError

import chz
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

import asyncio
import structlog.stdlib
import random
import string

import chz
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerInterface
import pandas as pd
from dataclasses import field
from dotenv.main import dotenv_values

logger = structlog.stdlib.get_logger(component=__name__, _print=True)

SWELancerSplit = Literal[
    "Diamond-$500k",
]

ALL_SPLITS: set[SWELancerSplit] = set(get_args(SWELancerSplit))

# Constant ENV vars
PUSHER_APP_KEY = "".join(random.choices(string.ascii_letters + string.digits, k=20))
PUSHER_APP_SECRET = "".join(random.choices(string.ascii_letters + string.digits, k=20))
PUSHER_APP_ID = "".join(random.choices(string.digits, k=7))


class SwelancerInstance(TypedDict):
    repo: str


def tests_failed_in_pytest_log(pytest_log: str) -> bool:
    lines = pytest_log.split("\n")
    summary_pattern = re.compile(r"=+\s+(\d+)\s+failed.*in\s+[\d\.]+s")

    return any(summary_pattern.search(line) for line in lines)

class SWELancerGrade(Grade):
    patch_path: str
    grade_report_path: str | None


class SWELancerTask(ComputerTask):
    instance: SwelancerInstance | None
    price: float
    variant: str
    acceptable_folders: list[str] = []
    manager_data: dict[str, Any] | None = None
    manager_commit: str | None = None
    
    retry_message: str = "The task isn't complete yet! You must write your output to this path exactly: '/app/expensify/manager_decisions.json'. You cannot submit to /mnt/data!"         
    
    # Install jupyter in the correct conda environment and start it within that environment.
    jupyter_setup: Sequence[str] | None = (
        "bash",
        "-c",
        "conda run -n testbed pip install jupyter && conda run -n testbed jupyter kernel --ip 0.0.0.0",
    )
    cwd: str = "/app/expensify"

    @override
    async def _setup(self, computer: ComputerInterface) -> None:
        # Assert various things about the environment
        print("SETUP")
        if isinstance(computer, JupyterComputerInterface):
            await computer.check_execute(
                """import os; assert os.environ.get('CONDA_DEFAULT_ENV') == 'testbed', os.environ.get('CONDA_DEFAULT_ENV')""",
            )
            logger.info("Correct Jupyter environment is loaded.")

        if self.variant == "swe_manager":
            await computer.check_shell_command(f"bash -c 'git reset --hard {self.manager_commit}^'")
        else:
            print("Waiting for setup to be done")
            while True:
                res = await computer.send_shell_command("cat /setup_done.txt")
                if res.output.decode("utf-8").strip() == "done":
                    print("Setup is done")
                    break
                await asyncio.sleep(15)

        # Zip the tests directory with a password
        print('Zipping tests')
        await computer.check_shell_command(
            "apt-get install -y zip unzip"
        )
        await computer.check_shell_command(
            "cd /app/tests && zip -P 'secretpasswordhere' -r /app/tmp.zip . && mv /app/tmp.zip /app/tests.zip"
        )
        # Clear tests directory
        await computer.send_shell_command("rm -rf /app/tests")

        # Purge existing git repo and create a new one
        await computer.check_shell_command("rm -rf .git")
        await computer.check_shell_command("git init")
        await computer.send_shell_command("find / -type f -name '*.orig' -delete")

        # Create a temp commit to mark where the model's changes begin
        if self.variant == "ic_swe":
            await computer.check_shell_command("bash -c 'git add .'")
            await computer.check_shell_command(
                'bash -c \'git -c user.name="temp" -c user.email="temp@example.com" commit -m "temp"\''
            )
            print("Temp commit created")

    @override
    async def check_for_valid_submission(self, computer: ComputerInterface) -> bool:
        if self.variant == "ic_swe":
            res = await computer.check_shell_command("cd /app/expensify && git diff HEAD")
            output = res.output.decode("utf-8").strip()
            return len(output) > 0
        else:
            res = await computer.send_shell_command("cat /app/expensify/manager_decisions.json")
            output = res.output.decode("utf-8").strip()
            return len(output) > 0 and "No such file or directory" not in output

    @override
    async def grade(self, computer: ComputerInterface) -> SWELancerGrade:
        #Unzip locked testing files
        print('Unzipping tests')
        print(await computer.check_shell_command(
            "unzip -q -P 'secretpasswordhere' -o /app/tests.zip -d /app/tests"
        ))
        if self.variant == "swe_manager":
            # === Grade Manager Tasks ===

            manager_decisions = await computer.send_shell_command(
                """bash -c 'cat /app/expensify/manager_decisions.json'"""
            )
            manager_decisions_json = json.loads(manager_decisions.output.decode("utf-8"))
            print(manager_decisions_json)

            correct = 0.0
            correct_option = int(self.manager_data["game"]["correct_proposal"]["id"]) #type: ignore
            submitted_option = int(list(manager_decisions_json.values())[0])

            if submitted_option == correct_option:
                correct = 1.0
            else:
                correct = 0.0

            return SWELancerGrade(
                score=correct,
                grader_log=json.dumps(
                    {
                        "earned": self.price * correct,
                        "available": self.price,
                        "variant": self.variant,
                    }
                ),
                patch_path="",
                grade_report_path="",
            )

        # === Grade SWE Tasks ===
        sample_id = f"{self.question_id}.{self.attempt_id}.{self.retry_idx}-{str(uuid4())}"
        logger.info("Grading task...", instance_id=sample_id)

        try:
            await computer.check_shell_command(
                "git -c core.fileMode=false diff --binary HEAD > /tmp/patch.diff"
            )
            model_patch = await computer.download("/tmp/patch.diff")
        finally:
            pass
        
        grading_computer = computer 

        # First, we need to identify all applicable test folders.
        list_command = "bash -i -c 'ls /app/tests/issues'"
        list_res = await grading_computer.send_shell_command(list_command)
        folders = list_res.output.decode("utf-8").splitlines()
        filtered_folders = [
            folder for folder in folders if not folder.startswith("Reintroduce-")
        ]

        # Get the raw GitHub issue ID from the Question ID
        issue_id = self.question_id.replace("Reintroduce-", "").split("_")[0]
        matching_folders = [
            folder for folder in filtered_folders if folder.split("_")[0] == issue_id
        ]
        print(f"Running n={len(matching_folders)} tests for {issue_id}.")

        test_results = []
        pytest_outputs = []
        num_failed = 0
        for env_issue_id in matching_folders:
            try:
                # Set the ISSUE_ID environment variable
                set_env_command = f"""echo "export ISSUE_ID={env_issue_id}" >> ~/.bashrc"""
                await grading_computer.send_shell_command(f"bash -i -c '{set_env_command}'")
                await grading_computer.send_shell_command(
                    f"""mkdir -p /app/tests/logs/{env_issue_id}"""
                )

                res = await grading_computer.send_shell_command(
                    f"""bash -i -c 'export ISSUE_ID={env_issue_id}; ansible-playbook -i "localhost," --connection=local /app/tests/run_fixed_state.yml'"""
                )
                print(f"Ansible playbook output: {res.output.decode('utf-8')}")

                pytest_log = await grading_computer.send_shell_command(
                    f"""bash -i -c 'export ISSUE_ID={env_issue_id}; cat /app/tests/logs/$ISSUE_ID/pytest.log'"""
                )

                pytest_output = pytest_log.output.decode("utf-8")
                pytest_outputs.append(pytest_output)
                print(f"Pytest output: {pytest_output}")

                # Entire test broke!
                if "No such file or directory" in pytest_output:
                    num_failed += 1
                    continue

                if tests_failed_in_pytest_log(pytest_output):
                    test_results.append(0.0)
                else:
                    # End early if it's wrong
                    test_results.append(1.0)
                    break
            except Exception as e:
                print("Grading error... retrying!")
                print(str(e))

        if not test_results:
            raise RetryableSystemError("No tests were executed.")

        print(f"Test results: {test_results}")
        correct = 1.0 if all(result == 1.0 for result in test_results) else 0.0

        return SWELancerGrade(
            score=correct,
            grader_log=json.dumps(
                {
                    "earned": self.price * correct,
                    "available": self.price,
                    "pytest_logs": pytest_outputs,
                    "variant": self.variant,
                    "model_patch": model_patch.decode("utf-8"),

                    # You can compute this using percentage of tests passed, how far along the e2e test got, etc.
                    "partial_credit": correct
                }
            ),
            patch_path="",
            grade_report_path="",
        )


@chz.chz
class SWELancerEval(PythonCodingEval):
    split: SWELancerSplit = "Diamond-$500k"
    taskset: list[str] | None = None

    @override
    def get_name(self) -> str:
        return "SWELancer"

    @override
    async def get_tasks(self) -> list[SWELancerTask]:
        tasks = pd.read_csv("swelancer_tasks.csv")
        env_vars = dotenv_values(".env")    
        SWEFL_ENV = {
            "PUSHER_APP_KEY": PUSHER_APP_KEY,
            "PUSHER_APP_SECRET": PUSHER_APP_SECRET, 
            "PUSHER_APP_ID": PUSHER_APP_ID,
            "USE_WEB_PROXY": env_vars["USE_WEB_PROXY"],
            "EXPENSIFY_URL": env_vars["EXPENSIFY_URL"],
            "NEW_EXPENSIFY_URL": env_vars["NEW_EXPENSIFY_URL"],
            "ISSUE_ID": "0",
            "LC_ALL": "C.UTF-8",
            "EVAL_VARIANT": "ic_swe",
        }

        docker_image = "swelancer:latest"

        swelancer_tasks = []
        i = 0 
        for task in tasks.to_dict(orient="records"):
            if self.taskset and task["question_id"] not in self.taskset:
                continue
            # task['all_proposals'] = ast.literal_eval(task['all_proposals'])
            task['prompt'] = ast.literal_eval(task['prompt'])
            task['acceptable_folders'] = ast.literal_eval(task['acceptable_folders'])
            if str(task['manager_data']) == 'nan': 
                task['manager_data'] = None
            else:
                task['manager_data'] = ast.literal_eval(task['manager_data'])

            if str(task['manager_commit']) == 'nan': 
                task['manager_commit'] = None
            if "Reintroduce-" in task["question_id"]:
                continue

            SWEFL_ENV["ISSUE_ID"] = task["question_id"]

            del task['price_limit']
            if 'canary' in task:
                del task['canary']
            swelancer_tasks.append(SWELancerTask(**task, attempt_id=str(i), environment=SWEFL_ENV, grade_every_step=False, docker_image=docker_image, instance=SwelancerInstance(repo="expensify"))) # type: ignore
            i += 1
        return swelancer_tasks
    
    @override
    async def evaluate(self, task: ComputerTask) -> FinalResult:
        last_convo = None
        
        # Create logs directory if it doesn't exist
        os.makedirs("conversation_logs", exist_ok=True)
        
        # Create unique log file name using task and attempt IDs
        log_filename = f"conversation_logs/{task.question_id}_{task.attempt_id}_{task.retry_idx}.jsonl"
        
        async with generator_with_cleanup(self.solver.run(task)) as gen:
            async for step in gen:
                if step.convo:
                    last_convo = step.convo
                    # Log each conversation step
                    print(f"Logging conversation step to {log_filename}")
                    with open(log_filename, 'a') as f:
                        log_entry = {
                            'timestamp': str(pd.Timestamp.now()),
                            'question_id': task.question_id,
                            'attempt_id': task.attempt_id,
                            'retry_idx': task.retry_idx,
                            'conversation': strip_all_metadata(step.convo)
                        }
                        f.write(json.dumps(log_entry) + '\n')

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
                    await asyncio.sleep(10) # time to shut down the docker container
                    return step

        raise ValueError("Solver did not return a final result! This is a bug.")

    @override
    async def get_summary(self, results: list[tuple[ComputerTask, FinalResult]]) -> dict[str, Any]:
        """
        Generate a summary of all evaluation results, including a breakdown of earnings and correctness per subtask.
        """
        logger.info("Generating summary of results.")
        try:
            # Get the original summary from the superclass method
            original_summary = await super().get_summary(results)
            original_summary["total_earnings"] = 0.0
            original_summary["total_available"] = 0.0

            # Initialize metadata variants
            original_summary["metadata_variants"] = {
                "accuracy": {
                    "ic_swe": 0.0,
                    "swe_manager": 0.0,
                    "ic_swe_hard": 0.0,
                    "swe_manager_hard": 0.0,
                },
                "earnings": {
                    "ic_swe": 0.0,
                    "swe_manager": 0.0,
                    "ic_swe_hard": 0.0,
                    "swe_manager_hard": 0.0,
                },
                "available": {
                    "ic_swe": 0.0,
                    "swe_manager": 0.0,
                    "ic_swe_hard": 0.0,
                    "swe_manager_hard": 0.0,
                },
            }

            # Counters for accuracy calculation
            variant_counts = {
                "ic_swe": {"correct": 0, "total": 0},
                "swe_manager": {"correct": 0, "total": 0},
                "ic_swe_hard": {"correct": 0, "total": 0},
                "swe_manager_hard": {"correct": 0, "total": 0},
            }

            partial_credit_sum = 0.0
            partial_credit_count = 0

            for task, result in results:
                try:
                    grader_log = json.loads(result.grade.grader_log)
                    earned = grader_log.get("earned", 0.0)
                    available = grader_log.get("available", 0.0)
                    variant = grader_log.get("variant", "")
                    assert variant in ["ic_swe", "swe_manager"], f"Unknown variant: {variant}"

                    # Update total earnings and available
                    original_summary["total_earnings"] += earned
                    original_summary["total_available"] += available

                    # Update variant-specific earnings and available
                    if variant in original_summary["metadata_variants"]["earnings"]:
                        original_summary["metadata_variants"]["earnings"][variant] += earned
                        original_summary["metadata_variants"]["available"][variant] += available

                        # Update accuracy counters
                        variant_counts[variant]["total"] += 1
                        if earned > 0:
                            variant_counts[variant]["correct"] += 1

                    # Check for hard tasks and update accordingly
                    if task.price > 300:  # type: ignore
                        hard_variant = f"{variant}_hard"
                        if hard_variant in original_summary["metadata_variants"]["accuracy"]:
                            # Update earnings and available for hard variants
                            original_summary["metadata_variants"]["earnings"][hard_variant] += earned
                            original_summary["metadata_variants"]["available"][hard_variant] += available

                            # Update accuracy counters for hard variants
                            variant_counts[hard_variant]["total"] += 1
                            if earned > 0:
                                variant_counts[hard_variant]["correct"] += 1

                    original_summary["pytest_log"] = grader_log.get("pytest_log", "No logs found")

                    # Compute partial credit for each task. Use provided partial_credit if available,
                    # otherwise derive it: if earned equals available (and available > 0), then full credit, else 0.
                    pc = grader_log.get("partial_credit")
                    if pc is None:
                        pc = 1.0 if (available > 0 and earned == available) else 0.0
                    partial_credit_sum += pc
                    partial_credit_count += 1

                except Exception as e:
                    print(str(e))

            # Calculate accuracy for each variant
            for variant in ["ic_swe", "swe_manager", "ic_swe_hard", "swe_manager_hard"]:
                correct = variant_counts[variant]["correct"]
                total = variant_counts[variant]["total"]
                if total > 0:
                    original_summary["metadata_variants"]["accuracy"][variant] = correct / total

            original_summary["average_partial_credit"] = partial_credit_sum / partial_credit_count if partial_credit_count else 0.0

            return original_summary

        except Exception as e:
            logger.exception("Failed to generate summary.")
            raise e
