import chz
import nanoeval
from nanoeval.eval import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.setup import nanoeval_entrypoint


async def main(gpqa: GPQAEval, runner: RunnerArgs) -> None:
    """
    Simple run script for GPQA.

    Example: run the GPQA eval using the production API.

    ```bash
    $ python -m nanoeval.examples.gpqa_simple \
        ...solver=nanoeval.solvers.mcq_api:MCQAPISolver \
        ...solver.model=gpt-4o
    ```
    """
    await nanoeval.run(EvalSpec(eval=gpqa, runner=runner))


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(main))
