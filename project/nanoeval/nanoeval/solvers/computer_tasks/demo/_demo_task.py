from openai.types.chat import ChatCompletionMessageParam
from pydantic import Field

from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerInterface
from nanoeval.solvers.computer_tasks.task import ComputerTask, Grade


class DemoTask(ComputerTask):
    question_id: str = "test"
    docker_image: str | None = "ubuntu"
    prompt: list[ChatCompletionMessageParam] = Field(
        default_factory=lambda: [
            {"role": "user", "content": "What is 7+7? Write your answer to /root/ANSWER.txt"}
        ]
    )

    async def _setup(self, computer: ComputerInterface) -> None:
        pass

    async def grade(self, computer: ComputerInterface) -> Grade:
        res = await computer.check_shell_command(
            "if [ -e /root/ANSWER.txt ]; then cat /root/ANSWER.txt; fi"
        )
        return Grade(
            score=1.0 if res.output.decode("utf-8", errors="ignore").strip() == "14" else 0.0,
            grader_log=f"Answer was {res}.",
        )
