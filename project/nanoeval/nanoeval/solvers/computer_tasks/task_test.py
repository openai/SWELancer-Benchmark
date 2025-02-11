from __future__ import annotations

from nanoeval.solvers.computer_tasks.task import ComputerTask, SimpleJupyterTask


def test_roundtrip_python_coding_task() -> None:
    # Tests that you can roundtrip a subclass of ComputerTask through json
    task = SimpleJupyterTask(
        question_id="test",
        prompt=[{"role": "user", "content": "hi!"}],
        setup_cell="",
        grader_cell="True",
    )
    serialized = task.model_dump()

    deserialized = ComputerTask.deserialize(serialized)
    assert isinstance(deserialized, SimpleJupyterTask)
    assert deserialized == task
