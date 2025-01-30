import asyncio
import json
import re
from typing import Any, Literal, Sequence, assert_never, get_args
from typing_extensions import TypedDict

from uuid import uuid4

import structlog.stdlib
from openai.types.chat import ChatCompletionMessageParam
from typing_extensions import override

import chz
from chat import chat
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

import chz
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerInterface
import pandas as pd

logger = structlog.stdlib.get_logger(component=__name__, _print=True)

SWELancerSplit = Literal[
    "Diamond-$500k",
]

ALL_SPLITS: set[SWELancerSplit] = set(get_args(SWELancerSplit))


class SwelancerInstance(TypedDict):
    repo: str


def tests_failed_in_pytest_log(pytest_log: str) -> bool:
    lines = pytest_log.split("\n")
    summary_pattern = re.compile(r"=+\s+(\d+)\s+failed.*in\s+[\d\.]+s")

    return any(summary_pattern.search(line) for line in lines)


def prompt_chatgpt(info: dict[str, Any]) -> list[ChatCompletionMessageParam]:
    return [
        {
            "role": "user",
            "content": f"""You are an expert software engineer maintaining the Expensify repository. It has already been cloned, and is present in /app/expensify (your CWD). You have been tasked with fixing the following issue:

{info["title"]}

{info["html_description"]}

The reward for the correct fix is ${info["price"]}. You do not need to push your changes to the repository, we will deal with this for you.

Do not attempt to run the app; simply make your changes and then end your turn. Do not end your turn until you have submitted your code changes. You absolutely must not leave action items / TODOs.
""",
        },
        {
            "role": "user",
            "content": """

You will be provided with a user tool, which you can call by running "bash -i -c 'user-tool'" in the command line, which has a user open the app with your local changes and perform the actions specified in the bug report. It could take up to a minute for the user to finish using the app. When you call the user tool, when the user finishes /app/expensify/user_tool/ will be populated with folders called output_browser1 … n for as many browsers as were used by the user during their test. Inside each folder, you will find a file called trace.trace, which contains the trajectory the user took. Here are a few things to note:

- Do not open the entire file; it may be extremely large. 
- If a row has “type":"screencast-frame”, then the “sha1” property will correspond to a .jpeg file in the resources folder, which is a screenshot of the browser at that time
- If you want to view the page as HTML, rather than a JPEG, you can look for rows that are called "type":"frame-snapshot”; you can print them out to see the HTML at this point in time
- You should review the rows with type "type" set to “log”, “before”, or “after”  as they are important and show what actions are being taken
- All of the rows are in order, so e.g. you can find an interesting log row and then look at the next row that is a frame-snapshot to see the HTML.

You should use this to help you iteratively debug and fix the issue. You can call it as often as you need to. 

When you call the user tool, you may need to wait up to 120 seconds for it to complete.""",
        },
    ]


def prompt_chatgpt_manager(
    info: dict[str, Any], proposals: list[dict[str, Any]]
) -> list[ChatCompletionMessageParam]:
    proposals_prompt = ""
    for proposal in proposals:
        try:
            # Start of selection
            proposals_prompt += (
                f"Proposal: {proposal['id']}:\n\n{proposal['content']}"
                + "\n\n--------------------------------------------\n\n"
            )
        except Exception as e:
            print(str(e))
            print(proposal)
    return [
        {
            "role": "user",
            "content": f"""You are an expert software engineering manager working on the Expensify repository. You have tasked your team with addressing the following issue:

{info["title"]}

{info["html_description"]}

You will be paid ${info["price"]} if your team fixes the issue. Since you are a manager, your task is to select the best proposal regaerding how to fix the issue from the below options:

{proposals_prompt}

---

For your convenience, the Expensify repository has already been cloned, and is present in /app/expensify (your CWD). You should not attempt to run the app or implement the entire fix, but you can review the codebase to understand the context of the issue.

When you are ready to submit your answer, please create a JSON file in /app/expensify/manager_decisions.json with the following format:

{{
    selected_proposal_id: int,
}}

You must write your output to this path exactly: '/app/expensify/manager_decisions.json'. You must not submit to anywhere in /mnt/data, just write to '/app/expensify/manager_decisions.json' exactly!
""",
        }
    ]


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
    
    # retry_message: str = "The task isn't complete yet! You can submit your answer using apply_patch via the command-line." 
    retry_message: str = "The task isn't complete yet! You must write your output to this path exactly: '/app/expensify/manager_decisions.json'. You cannot submit to /mnt/data!"         
    # Install jupyter in the correct conda environment and start it within that environment.
    # Ensures the model can properly run unit tests.
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
            # reset to the broken commit
            await computer.check_shell_command(f"bash -c 'git reset --hard {self.manager_commit}^'")
        else:
            # instead of a time based check, check until the SETUP_DONE environment variable is set
            print("Waiting for setup to be done")
            while True:
                res = await computer.send_shell_command("cat /setup_done.txt")
                if res.output.decode("utf-8").strip() == "done":
                    print("Setup is done")
                    break
                await asyncio.sleep(15)

        # Clear tests directory
        await computer.send_shell_command("rm -rf /app/tests")

        # Remove existing git repo and create a new one
        await computer.check_shell_command("rm -rf .git")
        await computer.check_shell_command("git init")

        # Creat a temp commit to mark where the model's changes begin
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
        if self.variant == "swe_manager":
            # === Grade Manager Tasks ===

            # cat the json file
            manager_decisions = await computer.send_shell_command(
                """bash -c 'cat /app/expensify/manager_decisions.json'"""
            )
            manager_decisions_json = json.loads(manager_decisions.output.decode("utf-8"))
            print(manager_decisions_json)

            # check if the manager decisions are correct
            correct = 0.0
            correct_option = int(self.manager_data["game"]["correct_proposal"]["id"])  # type: ignore
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

        with computer as grading_computer:
            # First, we need to identify all applicable test folders.
            list_command = "bash -i -c 'ls /app/tests/issues'"
            list_res = await grading_computer.send_shell_command(list_command)
            folders = list_res.output.decode("utf-8").splitlines()

            # Remove the folders that are from testbed variant tasks, since they share tests.
            filtered_folders = [
                folder for folder in folders if not folder.startswith("Reintroduce-")
            ]

            # Get the raw GitHub issue ID from the Question ID
            issue_id = self.question_id.replace("Reintroduce-", "").split("_")[0]

            # Find all relevant tests to run
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

                    # Run tests against the model's code
                    res = await grading_computer.send_shell_command(
                        f"""bash -i -c 'export ISSUE_ID={env_issue_id}; ansible-playbook -i "localhost," --connection=local /app/tests/run_fixed_state.yml'"""
                    )
                    print(f"Ansible playbook output: {res.output.decode('utf-8')}")

                    # Get pytest.log
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
                raise RuntimeError("No tests were executed.")

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
                    }
                ),
                patch_path="",
                grade_report_path="",
            )


@chz.chz
class SWELancerEval(PythonCodingEval):
    split: SWELancerSplit = "Diamond-$500k"

    @override
    def get_name(self) -> str:
        return "SWELancer"

    @override
    async def get_tasks(self) -> list[SWELancerTask]:
        tasks = pd.read_csv("swelancer_tasks.csv")
        return [SWELancerTask(**task) for task in tasks.to_dict(orient="records")]
    
    @override
    async def evaluate(self, task: ComputerTask) -> FinalResult:
        last_convo: chat.Conversation | None = None

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
                            original_summary["metadata_variants"]["earnings"][hard_variant] += (
                                earned
                            )
                            original_summary["metadata_variants"]["available"][hard_variant] += (
                                available
                            )

                            # Update accuracy counters for hard variants
                            variant_counts[hard_variant]["total"] += 1
                            if earned > 0:
                                variant_counts[hard_variant]["correct"] += 1

                    original_summary["pytest_log"] = grader_log.get("pytest_log", "No logs found")
                except Exception as e:
                    print(str(e))

            # Calculate accuracy for each variant
            for variant in ["ic_swe", "swe_manager", "ic_swe_hard", "swe_manager_hard"]:
                correct = variant_counts[variant]["correct"]
                total = variant_counts[variant]["total"]
                if total > 0:
                    original_summary["metadata_variants"]["accuracy"][variant] = correct / total

            return original_summary

        except Exception as e:
            logger.exception("Failed to generate summary.")
            raise e
