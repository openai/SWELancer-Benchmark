from __future__ import annotations

# Load environment before importing anything else
from dotenv import load_dotenv
load_dotenv()

import json
from swelancer import SWELancerEval 
import argparse
import nanoeval
from nanoeval.evaluation import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.recorder import dummy_recorder
from nanoeval.setup import nanoeval_entrypoint
from swelancer_agent import SimpleAgentSolver

def parse_args():
    parser = argparse.ArgumentParser(description='Run SWELancer evaluation')
    parser.add_argument('--issue_ids', nargs='*', type=str, help='List of ISSUE_IDs to evaluate. If not specified, all issues will be evaluated.')
    return parser.parse_args()

async def main() -> None:
    args = parse_args()
    taskset = args.issue_ids if args.issue_ids else []

    report = await nanoeval.run(
        EvalSpec(
            # taskset is a list of ISSUE_IDs you wish to evaluate (e.g., ["123", "456_789"])
            eval=SWELancerEval(
                solver=SimpleAgentSolver(model="deepseek-reasoner"),
                taskset=taskset
            ),
            runner=RunnerArgs(
                concurrency=25,
                experimental_use_multiprocessing=True,
                enable_slackbot=False,
                recorder=dummy_recorder(),
                max_retries=5
            ),
        )
    )
    print(report)

    if taskset and len(taskset) == 1:
        # Save the report to a JSON file based on task_id
        with open(f"report_{taskset[0]}.json", "w") as f:
            json.dump(report, f)

if __name__ == "__main__":
    nanoeval_entrypoint(main())
