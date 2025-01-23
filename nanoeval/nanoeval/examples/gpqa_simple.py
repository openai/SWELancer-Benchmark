"""
NOTE: If you don't have access to az://oaidatasets2, you should download
https://github.com/idavidrein/gpqa/blob/main/dataset.zip and unzip it.
Then, append the argument `...data_file=path/to/gpqa_diamond.csv` to the
commands below.

# Run eval using the post training completer stack.
$ python -m nanoeval.examples.gpqa_simple \
  ...solver=nanoeval.solvers.mcq_harmony:HarmonyMCQSolver \
  ...turn_completer=turn_completer.single_message_turn_completer:SingleMessageTurnCompleter.Config \
  ...message_completer=message_completer.token_message_completer:TokenMessageCompleter.Config \
  ...token_completer_config=legacy_rest_token_completer.legacy_rest_token_completer:LegacyRestTokenCompleter.Config \
  ...message_completer.renderer=... \
  ...token_completer_config.api_base=...

# Run eval using the production API.
$ python -m nanoeval.examples.gpqa_simple \
    ...solver=nanoeval.solvers.mcq_api:MCQAPISolver \
    ...solver.model=gpt-4o
"""

import chz
import nanoeval
from nanoeval.eval import EvalSpec, RunnerArgs
from nanoeval.examples._gpqa import GPQAEval
from nanoeval.setup import nanoeval_entrypoint


async def main(gpqa: GPQAEval, runner: RunnerArgs) -> None:
    await nanoeval.run(EvalSpec(eval=gpqa, runner=runner))


if __name__ == "__main__":
    nanoeval_entrypoint(chz.entrypoint(main))
