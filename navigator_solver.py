# navigator_solver.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import chz
from nanoeval.solvers.computer_tasks.solver import PythonCodingSolver
from nanoeval.solvers.computer_tasks.steps import Step, FinalResult, FinalResultSuccessful
from nanoeval.solvers.computer_tasks.task import ComputerTask
from nanoeval_alcatraz.task_to_alcatraz_config import task_to_alcatraz_config
from nanoeval_alcatraz.alcatraz_computer_interface import AlcatrazComputerInterface
from alcatraz.clusters.local import LocalConfig
import os
from pathlib import Path

# Decorate with chz to satisfy nanoeval requirements
@chz.chz
class NavigatorSolver(PythonCodingSolver):
    def shortname(self) -> str:              # shows up in the report
        return "navigator"

    @asynccontextmanager
    async def _start_computer(self, task: ComputerTask):
        print(f"Starting computer for task: {task}")
        # Build a detailed TASK description for the container environment. We prefer
        # the dataset instructions if they are available on the `task.prompt` field.
        # Fallbacks: str(task) or the question ID if all else fails.
        try:
            prompt = getattr(task, "prompt", None)
            if prompt:
                # `prompt` is typically a list of message dicts with a `content` key.
                if isinstance(prompt, list):
                    task_description = "\n".join(str(m.get("content", "")) for m in prompt)
                else:
                    task_description = str(prompt)
            else:
                task_description = str(task)
        except Exception:
            task_description = str(getattr(task, "question_id", "SWELancer"))

        cfg = task.model_copy(update={
            "docker_image": "navigator-agent:latest",
            "environment": {
                "CODEBASE_PATH": "/app/expensify",
                # Provide the full task instructions to the container so the agent can reason about them.
                "TASK": task_description,
                # Keep a simple identifier available separately for logging/metrics purposes.
                "TASK_ID": str(getattr(task, "question_id", "1")),
                "NO_REDIS": "1",            # tells navigator to start immediately
            },
        })
        # Determine which docker socket to use
        docker_host_env = os.environ.get("DOCKER_HOST")
        default_sock = "unix:///var/run/docker.sock"
        desktop_sock_path = os.path.expanduser("~/.docker/desktop/docker-cli.sock")

        if docker_host_env:
            docker_host = docker_host_env
        else:
            # If the default socket doesn't exist but the Docker-Desktop one does, use that.
            if not os.path.exists(default_sock[len("unix://"):]) and os.path.exists(desktop_sock_path):
                docker_host = f"unix://{desktop_sock_path}"
            else:
                docker_host = default_sock
        # Debug: show which docker socket/host we are using and whether it exists
        print("[NavigatorSolver] Using docker_host:", docker_host)
        if docker_host.startswith("unix://"):
            sock_path = docker_host[len("unix://"):]
            print("[NavigatorSolver] Socket path exists?", os.path.exists(sock_path))
        else:
            print("[NavigatorSolver] Non-unix DOCKER_HOST")
        async with task_to_alcatraz_config(
            cfg,
            LocalConfig(pull_from_registry=False, docker_host=docker_host),
        ).build() as cluster:
            # Yield control to the caller while the container is running
            try:
                yield AlcatrazComputerInterface(cluster_value=cluster)
            finally:
                # Always attempt to fetch container logs (even on crash) and write to file
                try:
                    # Retrieve a large tail to capture all logs. Docker returns the last N lines; using a very large
                    # number effectively fetches the complete logs.
                    logs: bytes = await cluster.fetch_container_logs(tail=100000)

                    # Ensure logs directory exists
                    logs_dir = Path("container_logs")
                    logs_dir.mkdir(exist_ok=True)

                    # Compose filename with task identifiers when available
                    try:
                        filename = f"{getattr(task, 'question_id', 'unknown')}_{getattr(task, 'attempt_id', '0')}_{getattr(task, 'retry_idx', 0)}.log"
                    except Exception:
                        filename = "navigator_container.log"

                    logfile_path = logs_dir / filename
                    logfile_path.write_bytes(logs)

                    print(f"[NavigatorSolver] Container logs written to {logfile_path}")
                except Exception as e:
                    # We purposefully swallow all exceptions here so that log collection never crashes the main flow
                    print(f"[NavigatorSolver] Failed to fetch/write container logs: {e}")

    async def run(self, task: ComputerTask) -> AsyncGenerator[Step | FinalResult, None]:
        async with self._start_computer(task) as comp:
            await task.setup(comp)                       # puts repo under /root
            exec_res = comp.send_shell_command("while pgrep -f navigator-agent/main.py; do sleep 5; done")

            # Append this exec output to the same log file we create in _start_computer
            try:
                logs_dir = Path("container_logs")
                logs_dir.mkdir(exist_ok=True)

                filename = f"{getattr(task, 'question_id', 'unknown')}_{getattr(task, 'attempt_id', '0')}_{getattr(task, 'retry_idx', 0)}.log"
                logfile_path = logs_dir / filename

                with logfile_path.open("ab") as f:
                    f.write(b"\n\n===== python /app/navigator/main.py output =====\n")
                    f.write(exec_res.output)
                    f.write(b"\n===== end =====\n")
            except Exception as e:
                print(f"[NavigatorSolver] Failed to append main.py output to log: {e}")
            grade = await task.grade(comp)               # runs unit tests
            yield FinalResultSuccessful(grade=grade)