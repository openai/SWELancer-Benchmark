# Computer Tasks

Computer tasks are a type of task that involve code execution on one or more containers. They are defined in
`nanoeval.solvers.computer_tasks.task:ComputerTask`.

## Overall flow

1. A `ComputerRuntime` starts a rollout from a `ComputerTask`, calls `task.setup()` and returns an implementation of
   `ComputerInterface`.
2. The agent gets a `ComputerInterface` and can call arbitrary functions using `computer.send_shell_command` or
   `computer.execute`.
3. When the agent is done, the eval calls `task.grade()`, which returns the score from the eval.