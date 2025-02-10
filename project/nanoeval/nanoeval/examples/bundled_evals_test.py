import pytest

from nanoeval.eval import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.solvers.mcq import MockSolver


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spec",
    [EvalSpec(eval=GPQAEval(solver=MockSolver()), runner=RunnerArgs())],
    ids=lambda spec: spec.eval.get_name(),
)
async def test_eval_self_test(spec: EvalSpec) -> None:
    """
    Runs the self-test for the eval. This checks basic things, like that the summary functions work correctly and the tasks can be loaded.
    """
    await spec.eval.self_test()
