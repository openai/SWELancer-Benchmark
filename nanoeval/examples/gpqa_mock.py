from __future__ import annotations

import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.json_recorder import json_recorder
from nanoeval.setup import nanoeval_entrypoint
from nanoeval.solvers.mcq import MockSolver


async def main() -> None:
    # smoke test for data loading, validation, solving
    report = await nanoeval.run(
        EvalSpec(
            eval=GPQAEval(solver=MockSolver()),
            runner=RunnerArgs(
                experimental_use_multiprocessing=False,
                enable_slackbot=True,
                recorder=json_recorder(),
            ),
        )
    )
    assert "accuracy" in report


if __name__ == "__main__":
    nanoeval_entrypoint(main())
