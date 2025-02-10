from __future__ import annotations

import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.json_recorder import json_recorder
from nanoeval.setup import nanoeval_entrypoint
from nanoeval.solvers.mcq_api import OpenAIAPIMCQSolver


async def main() -> None:
    # smoke test for data loading, validation, solving
    report = await nanoeval.run(
        EvalSpec(
            eval=GPQAEval(solver=OpenAIAPIMCQSolver(model="gpt-4o")),
            runner=RunnerArgs(
                concurrency=4096,
                experimental_use_multiprocessing=True,
                enable_slackbot=True,
                recorder=json_recorder(),
            ),
        )
    )
    assert "accuracy" in report


if __name__ == "__main__":
    nanoeval_entrypoint(main())
