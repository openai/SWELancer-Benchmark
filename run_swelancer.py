from __future__ import annotations
from swelancer import SWELancerEval 

import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.recorder import dummy_recorder
from nanoeval.setup import nanoeval_entrypoint
from swelancer_agent import SimpleAgentSolver

async def main() -> None:
    report = await nanoeval.run(
        EvalSpec(
            eval=SWELancerEval(solver=SimpleAgentSolver(model="gpt-4o")),
            runner=RunnerArgs(
                concurrency=1,
                experimental_use_multiprocessing=False,
                enable_slackbot=False,
                recorder=dummy_recorder(),
            ),
        )
    )
    print(report)


if __name__ == "__main__":
    nanoeval_entrypoint(main())