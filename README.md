# SWE-Lancer

This repo contains the dataset and code for the paper ["SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?"](https://www.openai.com/index/swe-lancer/).

---

Thank you so much for checking out our benchmark! If you have questions, run into issues, or want to contribute, please open an issue or pull request. You can also reach us at samuelgm@openai.com and michele@openai.com at any time.

We will continue to update this repository with the latest tasks, updates to the scaffolding, and improvements to the codebase

- If you'd like to use the latest version, please use the `main` branch.

- If you'd like to use the version of the dataset from the paper and codebase at time of paper release, please check out the `paper` branch. Note that the performance outlined in our paper is on our internal scaffold. We've aimed to open-source as much of it as possible, but the open-source agent and harness may not be exactly the same.

---

**Step 1: Package Management and Requirements**

[Calkit](https://github.com/calkit/calkit) is used to
manage the necessary [Docker](https://docker.com) and
[uv](https://github.com/astral-sh/uv) environments,
so all three of these tools must be installed.

**Step 2: Run the Docker Container**

Run the Docker container, building if necessary, by executing:

```bash
calkit xenv -n docker-arm64 -- ISSUE_ID=1 bash /app/tests/run.sh
```

If you are running on an AMD64 (x86) platform, replace `docker-arm64` with
`docker-amd64` in the command above.

**Step 2: Check Environmental Variables**

To ensure environmental variables are set properly, execute:

```bash
calkit check env-vars
```

You will be prompted for any missing environmental variables,
e.g., `OPENAI_API_KEY`,
and these will be added to a `.env` file, which will be ignored by Git.

**Step 3: Running SWE-Lancer**

You are now ready to run the eval with:

```bash
calkit run
```

You should immediately see logging output as the container gets set up and the tasks are loaded, which may take several minutes. You can adjust the model, concurrency, recording, and other parameters in `run_swelancer.py`.

## Running at Scale

To run SWELancer at scale in your own environment, you'll need to implement your own compute infrastructure. Here's a high-level overview of how to integrate SWELancer with your compute system:

### 1. Implement a Custom ComputerInterface

Create your own implementation of the `ComputerInterface` class that interfaces with your compute infrastructure. The main methods you need to implement are:

```python
class YourComputerInterface(ComputerInterface):
  async def send_shell_command(self, command: str) -> CommandResult:
    """Execute a shell command and return the result"""
    pass
  async def upload(self, local_path: str, remote_path: str) -> None:
    """Upload a file to the compute environment"""
    pass
  async def download(self, remote_path: str) -> bytes:
    """Download a file from the compute environment"""
    pass
  async def check_shell_command(self, command: str) -> CommandResult:
    """Execute a shell command and raise an error if it fails"""
    pass
    async def cleanup(self) -> None:
    """Clean up any resources"""
    pass
```

### 2. Update the Computer Start Function

Modify `swelancer_agent.py`'s `_start_computer` function to use your custom interface:

```python
async def _start_computer(self, task: ComputerTask) -> AsyncGenerator[ComputerInterface, None]:
    # Implement your compute logic here

    # Initialize your compute environment
    # This could involve:
    # - Spinning up a container/VM
    # - Setting up SSH connections
    # - Configuring environment variables
    # Return your custom ComputerInterface implementation
    return YourComputerInterface()
```

### Reference Implementation

For a complete example of a ComputerInterface implementation, you can refer to the `alcatraz_computer_interface.py` file in the codebase. This shows how to:

- Handle command execution
- Manage file transfers
- Deal with environment setup
- Handle cleanup and resource management

### Best Practices

1. **Resource Management**

   - Implement proper cleanup in your interface
   - Handle container/VM lifecycle appropriately
   - Clean up temporary files

2. **Security**

   - Implement proper isolation between tasks
   - Handle sensitive data appropriately
   - Control network access

3. **Scalability**

   - Consider implementing a pool of compute resources
   - Handle concurrent task execution
   - Implement proper resource limits

4. **Error Handling**
   - Implement robust error handling
   - Provide meaningful error messages
   - Handle network issues gracefully

## Citation

```
@misc{miserendino2025swelancerfrontierllmsearn,
      title={SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?},
      author={Samuel Miserendino and Michele Wang and Tejal Patwardhan and Johannes Heidecke},
      year={2025},
      eprint={2502.12115},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2502.12115},
}
```
