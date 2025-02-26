# nanoeval

Simple, ergonomic, and high performance evals. We use it at OpenAI as part of our infrastructure to run Preparedness evaluations.

# Principles

1. **Minimal indirection.** You should be able to implement and understand an eval in 100 lines.
2. **Separation of concerns.** Keep data loading away from completions/parsing/different ways of running an eval.
3. **Fast iteration and testability.** nanoevals should import in less than a second and be testable without a live LLM backend.
4. **High performance**. Nanoeval should max out the compute resources available to it.

# Primitives

- `Eval` - A [chz](https://github.com/openai/chz) class. Enumerates a set of tasks, and (typically) uses a "Solver" to solve them and then records the results. Can be configured in code or on the CLI using a chz entrypoint.
- `EvalSpec` - An eval to run and runtime characteristics of how to run it (i.e. concurrency, recording, other administrivia)
- `Task` - A single scoreable unit of work.
- `Solver` - A strategy (usually involving sampling a model) to go from a task to a result that can be scored. For example, there may be different ways to prompt a model to answer a multiple-choice question (i.e. looking at logits, few-shot prompting, etc)

# Installation

```bash
# Using https://github.com/astral-sh/uv (recommended)
uv add "git+https://github.com/openai/SWELancer-Benchmark#egg=nanoeval&subdirectory=project/nanoeval"
# Using pip
pip install "git+https://github.com/openai/SWELancer-Benchmark#egg=nanoeval&subdirectory=project/nanoeval"
```

nanoeval is pre-release software and may have breaking changes, so it's recommended that you pin your installation to a specific commit. The uv command above will do this for you.

# Running your first eval

See [gpqa_api.py](nanoeval/examples/gpqa_api.py) for an implementation of GPQA using the OpenAI API in <70 lines of code.

# Features

## Core execution flow

At the highest level: nanoeval is just a library. You can import it and call `nanoeval.run()` on an EvalSpec. nanoeval then loads all the tasks and runs `eval.evaluate()` in parallel using asyncio.

More granularly: nanoeval operates like a tiny distributed system. Eval state is tracked in a per-process sqlite database in `/dev/shm` (or `/tmp` on macOS). When you call `.run()`, it queues up the eval and all of its tasks in sqlite. It then starts one or more executors that continually poll the db for new tasks, run them, and put the results back in the db.

The executors can operate in two modes:

1. **In-process:** The executor is just an async task running in the same process as the main eval script. The default.
2. **Multiprocessing:** Starts a pool of executor processes that all poll the db. Use this via `spec.runner.experimental_use_multiprocessing=True`.

## Performance

nanoeval has been tested up to ~5,000 concurrent rollouts. It is likely that it can go higher.

For highest performance, use multiprocessing with as many processes as your system memory + core count allows. See `RunnerArgs` for documentation.

## Monitoring

nanoeval has a tiny built-in monitor to track ongoing evals. It's a streamlit that visualizes the state of the internal run state database. This can be helpful to diagnose hangs on specific tasks. To use it:

```bash
# either set spec.runner.use_monitor=True OR run this command:
python3 -m nanoeval.bin.mon
```

## Resumption

Because nanoeval uses a persistent database to track the state of individual tasks in a run, you can restart an in-progress eval if it crashes. (In-progress rollouts will be restarted from scratch, but completed rollouts will be saved.) To do this:

```bash
# Restarts the eval in a new process
python3 -m nanoeval.bin.resume run_set_id=...
```

You can list all run sets (databases) using the following command:

```bash
ls -lh "$(python3 -c "from nanoeval.fs_paths import database_dir; print(database_dir())")"
```

The run set ID for each database is simply the filename, without the `.db*` suffix.

# Writing your first eval

An eval is just a `chz` class that defines `get_name()`, `get_tasks()`, `evaluate()` and `get_summary()`. Start with `gpqa_simple.py`; copy it and modify it to suit your needs. If necessary, drop down to the base `nanoeval.Eval` class instead of using `MCQEval`.

The following sections describe common use case needs and how to achieve them.

## Public API

You may import code from any `nanoeval.*` package that does not start with an underscore. Functions and classes that start with an underscore are considered private.

## Handling closable state

Many things you might want to use in an eval (e.g., external resources, tools) require one-time creation and cleanup. To accomodate this, `nanoeval.run` will `__aenter__` an eval on start and `__aexit__` on exit. We also have a simple wrapper for these functions called `HasAsyncContextManager` that lets you do something like this:

```python
from typing_extensions import override
from typing import AsyncGenerator
import chz
from nanoeval import Eval
from nanoeval.solvers.mcq import MCQTask, Answer, MCQSolver

@chz.chz
class MCQEval(Eval[MCQTask, Answer]):
    solver: MCQSolver
    n_consensus: int = 1

    @override
    async def _context(self) -> AsyncGenerator[None, None]:
        async with self.solver:
            yield
```

# Debugging

## Kill dangling executors

Nanoeval uses `multiprocessing` to execute rollouts in parallel. Sometimes, if you ctrl-c the main job, the multiprocessing executors don’t have time to exit. A quick fix:

```bash
pkill -f multiprocessing.spawn
```

## Debugging stuck runs

`py-spy` is an excellent tool to figure out where processes are stuck if progress isn’t happening. You can check the monitor to find the PIDs of all the executors and py-spy them one by one. The executors also run `aiomonitor`, so you can connect to them via `python3 -m aiomonitor.cli ...` to inspect async tasks.

## Diagnosing main thread stalls

nanoeval relies heavily on Python asyncio for concurrency within each executor process; thus, if you block the main thread, this will harm performance and lead to main thread stalls. A common footgun is making a synchronous LLM or HTTP call, which can stall the main thread for dozens of seconds.

Tracking down blocking calls can be annoying, so nanoeval comes with some built-in features to diagnose these.

1. Blocking synchronous calls will trigger a stacktrace dump to a temporary directory. You can see them by running `open "$(python3 -c "from nanoeval.fs_paths import stacktrace_root_dir; print(stacktrace_root_dir())")"`.
2. Blocking synchronous calls will also trigger a console warning.
