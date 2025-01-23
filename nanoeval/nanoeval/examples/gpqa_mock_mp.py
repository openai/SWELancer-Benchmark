from __future__ import annotations

import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.recorder import dummy_recorder
from nanoeval.setup import nanoeval_entrypoint
from nanoeval.solvers.mcq import MockSolver


async def main() -> None:
    # smoke test for data loading, validation, solving
    args = RunnerArgs(
        concurrency=100,
        num_processes=10,
        experimental_use_multiprocessing=True,
        enable_slackbot=False,
        recorder=dummy_recorder(),
    )
    spec = EvalSpec(
        eval=GPQAEval(n_consensus=16, solver=MockSolver()),
        runner=args,
    )
    report = await nanoeval.run(spec)
    assert "accuracy" in report


if __name__ == "__main__":
    nanoeval_entrypoint(main())
