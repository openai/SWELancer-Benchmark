import chz
from nanoeval.solvers.computer_tasks.solver import PythonCodingSolver
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerInterface
from nanoeval.solvers.computer_tasks.solver import PythonCodingEval
from nanoeval.solvers.computer_tasks.steps import FinalResult, FinalResultSuccessful, FinalResultWithException, Step
from nanoeval.solvers.computer_tasks.task import ComputerTask, Grade
from typing_extensions import override
import shlex

import asyncio
import os
import re
import uuid
import json
import traceback
import time
import builtins
from contextlib import asynccontextmanager
from textwrap import dedent
from typing import AsyncGenerator, Dict, Optional, Any, List

# Import the MorphCloud client
from morphcloud.api import MorphCloudClient

# OpenAI imports remain the same
from openai import OpenAI
import os
import tiktoken

# Save the original print function for timed logging
original_print = builtins.print

# Record start time
start_time = time.time()

# Create a custom print function that shows elapsed time
def timed_print(*args, **kwargs):
    elapsed = time.time() - start_time
    original_print(f"[{elapsed:.3f}s]", *args, **kwargs)

# Replace the built-in print function
builtins.print = timed_print

COLORS = {'GREEN': '\033[32m', 'RESET': '\033[0m'}

# Helper function to safely decode bytes or return strings as is
def safe_decode(data):
    """Safely decode bytes or return the string as is."""
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    return data

# OpenAI utility functions
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def count_tokens(messages: list[dict[str, Any]], model: str = "gpt-4") -> int:
    """Count the number of tokens in a list of messages."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    
    for message in messages:
        # Every message follows format: {"role": role, "content": content}
        num_tokens += 4  # Every message follows format: <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(encoding.encode(str(value)))
    
    return num_tokens

def trim_messages(messages: list[dict[str, Any]], max_tokens: int, model: str = "gpt-4") -> list[dict[str, Any]]:
    """Trim messages to fit within token limit by removing older messages."""
    while len(messages) > 1 and count_tokens(messages, model) > max_tokens:
        messages.pop(1)
    return messages

def get_model_response(messages: list[dict[str, Any]]) -> str:
    messages = trim_messages(messages, 110000)
    
    chat_completion = client.chat.completions.create(
        messages=messages, # type: ignore
        model="gpt-4o",
    )
    return chat_completion.choices[0].message.content # type: ignore

# Define our function to convert task to MorphCloud configuration
def task_to_morph_config(task: ComputerTask) -> "MorphConfig":
    """Convert a ComputerTask to a MorphCloud configuration"""
    updated_environment = task.environment.copy()

    issue_id = updated_environment.get("ISSUE_ID", "")

    # Infer EVAL_VARIANT based on ISSUE_ID
    if "manager" in issue_id.lower():
        eval_variant = "swe_manager"
    else:
        eval_variant = "ic_swe"

    updated_environment["EVAL_VARIANT"] = eval_variant

    return MorphConfig(
        docker_image=task.docker_image,
        environment=updated_environment,
        resources={
            "vcpus": 4,
            "memory": 8192,  # 8GB in MB
            "disk_size": 20480  # 20GB in MB
        }
    )

import asyncio
import time

async def run_mitmdump_in_container(instance, container_name):
    """Run mitmdump inside the container during initialization"""
    print(f"Running mitmdump in container {container_name} during initialization...")
    
    # Make sure container is started but don't wait for full initialization
    check_started = await instance.aexec(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
    if "Up" not in safe_decode(check_started.stdout):
        print("Waiting for container to at least start...")
        for _ in range(10):  # Try for up to 10 seconds
            await asyncio.sleep(1)
            check_again = await instance.aexec(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
            if "Up" in safe_decode(check_again.stdout):
                print("Container is now up")
                break
        else:
            print("Warning: Container did not start properly")
            return False
    
    # Run mitmdump with timeout
    mitm_cmd = f"docker exec {container_name} timeout 20s mitmdump --set confdir=~/.mitmproxy --mode transparent --showhost"
    mitm_result = await instance.aexec(mitm_cmd)
    
    # Print results
    print(f"mitmdump command completed with exit code: {mitm_result.exit_code}")
    if mitm_result.exit_code == 124:
        print("mitmdump exited due to timeout (expected behavior)")
    
    # Verify certificate creation
    cert_check = await instance.aexec(
        f"docker exec {container_name} bash -c \"test -f /root/.mitmproxy/mitmproxy-ca-cert.pem && echo 'Certificate exists' || echo 'Certificate not found'\""
    )
    cert_status = safe_decode(cert_check.stdout).strip()
    print(f"Certificate status: {cert_status}")
    
    return "Certificate exists" in cert_status

# Execution result class compatible with the interface
class ExecutionResult:
    """Compatible ExecutionResult class for ComputerInterface"""
    def __init__(self, output: bytes, exit_code: int):
        self.output = output
        self.exit_code = exit_code

# Define our MorphConfig class
class MorphConfig:
    def __init__(self, docker_image: str, resources: Dict[str, int], environment: Dict[str, str] = None):
        self.docker_image = docker_image
        self.resources = resources
        self.client = MorphCloudClient(api_key=os.environ.get("MORPH_API_KEY"))
        self.base_snapshot_metadata = {
            "purpose": "swelancer-base",
            "status": "ready"
        }
        # New: Add specific SWE-Lancer metadata
        self.swelancer_metadata = {
            "purpose": "swelancer-built-image",
            "description": "SWELancer-Benchmark with Docker image built"
        }
        self.environment = environment or {}

    @asynccontextmanager
    async def build(self, cleanup_on_error=True) -> AsyncGenerator["MorphCloudValue", None]:
        """Build and return a MorphCloudValue that contains the necessary configuration"""
        # First check for an existing SWELancer snapshot with the image already built
        print("Looking for existing SWELancer snapshot...")
        swelancer_snapshots = await self.client.snapshots.alist(
            metadata=self.swelancer_metadata
        )
        
        if swelancer_snapshots:
            print(f"Found existing SWELancer snapshot with ID: {swelancer_snapshots[0].id}")
            snapshot_id = swelancer_snapshots[0].id
        else:
            # If no SWELancer snapshot, check for or create a base snapshot
            print("No existing SWELancer snapshot found, will build image...")
            snapshot_id = await self._ensure_base_snapshot()
        
        # Start an instance
        print(f"Starting instance from snapshot {snapshot_id}...")
        instance = await self.client.instances.astart(snapshot_id)
        await instance.await_until_ready()
        print(f"Instance is ready.: {instance.id}")
        
        try:
            # Check Docker status first
            with instance.ssh() as ssh:
                print("Checking Docker status")
                docker_status = ssh.run(["systemctl", "status", "docker.service", "--no-pager", "-n", "20"], timeout=10)
                
                if "active (running)" not in docker_status.stdout:
                    print("Docker not running. Starting Docker...")
                    ssh.run(["systemctl", "start", "docker.service"]).raise_on_error()
            
            # If we're using a SWELancer snapshot, we should already have the image
            if swelancer_snapshots:
                # Verify image exists
                image_check = await instance.aexec(f"docker images -q {self.docker_image}")
                if not safe_decode(image_check.stdout).strip():
                    print(f"Warning: Image {self.docker_image} not found in snapshot. Will attempt to build it.")
                    await self._build_swelancer_image(instance)
            else:
                # Otherwise, we need to build the image
                await self._build_swelancer_image(instance)
            
            # Start container with a unique name
            container_name = f"swelancer-{uuid.uuid4().hex[:8]}"
            
            # Run the container using the successful method from tests.py
            print(f"Starting container: {container_name}")
            print(f'environment: {self.environment.items()}')
            
            import shlex
            env_args = ' '.join([f'-e {shlex.quote(f"{key}={value}")}' for key, value in self.environment.items()])
            
            print(env_args)
            # make sure our ssh is a login
            # manually source bashrc
            network_mode = "host"

            # stdin_open True -i
            # tty True -t
            # detach True -d

            docker_run_cmd = f"""
                docker run -d \
                  --name {container_name} \
                  -u 0 \
                  --privileged \
                  --network={network_mode} \
                  -i -t \
                  {env_args} \
                  {self.docker_image}
                """

            # docker_run_cmd = f"docker run -d --name {container_name} {env_args} {self.docker_image}"

            print(f"Executing Docker run command: {docker_run_cmd}")
            run_result = await instance.aexec(docker_run_cmd)

            if run_result.exit_code != 0:
                error_message = (
                    f"Failed to start container '{container_name}' with default ENTRYPOINT/CMD.\n"
                    f"Docker command: {docker_run_cmd}\n" # Include the docker run command in error message
                    f"Exit Code: {run_result.exit_code}\n"
                    f"Stderr: {safe_decode(run_result.stderr)}\n"
                )
                print(error_message)
                # Debug output: Print container logs on failure to start
                logs_result = await instance.aexec(f"docker logs {container_name}")
                print(f"Container logs on startup failure:\n{safe_decode(logs_result.stdout)}\n{safe_decode(logs_result.stderr)}")
                # Debug output: Inspect ENTRYPOINT and CMD on failure
                inspect_result = await instance.aexec(f"docker inspect --format='{{{{.Config.Entrypoint}}}} {{{{ .Config.Cmd }}}}' {container_name}")
                print(f"Container ENTRYPOINT/CMD on failure: {safe_decode(inspect_result.stdout)}")
                raise RuntimeError(error_message)
            else:
                print(f"Container '{container_name}' started successfully using default ENTRYPOINT/CMD.")
                # Debug output: Inspect ENTRYPOINT and CMD on successful start
                inspect_result = await instance.aexec(f"docker inspect --format='{{{{.Config.Entrypoint}}}} {{{{ .Config.Cmd }}}}' {container_name}")
                print(f"Container ENTRYPOINT/CMD on successful start: {safe_decode(inspect_result.stdout)}")

            # Verify the container is running
            check_result = await instance.aexec(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
            # Debug output: Print full check_result for container status
            print(f"Container status check result: Exit Code: {check_result.exit_code}, Stdout: {safe_decode(check_result.stdout)}, Stderr: {safe_decode(check_result.stderr)}")
            print(f"Container status (just stdout): {safe_decode(check_result.stdout)}") # Keep existing shorter status printout for easier readability
            # Run mitmdump during initialization (before considering setup complete)
            mitm_success = await run_mitmdump_in_container(instance, container_name)
            if not mitm_success:
                print("Warning: mitmproxy inject may not have completed successfully")
            else:
                ("mitmproxy inject successful")
            
            # Verify the container is still running after mitmdump
            check_result = await instance.aexec(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
            print(f"Container status after mitmdump: {safe_decode(check_result.stdout)}")

            if "Up" not in safe_decode(check_result.stdout):
                print("ERROR: Container failed to start (based on 'docker ps' check)")
                # Debug output: Print container logs if 'docker ps' check fails
                logs_result_fail_check = await instance.aexec(f"docker logs {container_name}")
                print(f"Container logs on 'docker ps' failure:\n{safe_decode(logs_result_fail_check.stdout)}\n{safe_decode(logs_result_fail_check.stderr)}")
                raise RuntimeError("Container failed to start (based on 'docker ps' check)")

            print(f"Container {container_name} started successfully")

            # Create and yield MorphCloudValue
            yield MorphCloudValue(instance=instance, container_name=container_name)

        except Exception as e:
            # If an error occurs and cleanup_on_error is False, don't stop the instance
            print(f"Error occurred: {str(e)}")
            print(f"Instance ID: {instance.id} - Container: {container_name}")
            if not cleanup_on_error:
                print(f"DEBUG MODE: Keeping instance '{instance.id}' running for debugging")
                # Just yield the value so it can be used for debugging
                yield MorphCloudValue(instance=instance, container_name=container_name)
                # Exit without cleanup
                return
            raise  # Re-raise the exception
        finally:
            # Only clean up if cleanup_on_error is True
            if cleanup_on_error:
                try:
                    # Attempt to stop the container if it exists
                    await instance.aexec(f"docker stop {container_name}")
                    await instance.aexec(f"docker rm {container_name}")
                except Exception as e:
                    print(f"Container cleanup error (non-critical): {str(e)}")
                    
                # Stop the instance only if cleanup_on_error is True
                print(f"Stopping instance {instance.id}")
                await instance.astop()
            else:
                print(f"DEBUG MODE: Instance {instance.id} left running with container {container_name}")
    
    async def _build_swelancer_image(self, instance) -> None:
        """Build the SWELancer Docker image on the instance"""
        print("Building SWELancer Docker image...")
        
        with instance.ssh() as ssh:
            # Clone the repo
            print("Cloning SWELancer repository...")
            ssh.run(["rm", "-rf", "SWELancer-Benchmark"]).raise_on_error()  # Remove if exists
            clone_result = ssh.run(["git", "clone", "https://github.com/openai/SWELancer-Benchmark.git"], timeout=60)
            if clone_result.exit_code != 0:
                print(f"Error cloning repository: {clone_result.stderr}")
                raise RuntimeError(f"Failed to clone repository: {clone_result.stderr}")
            
            # Get current directory
            pwd_result = ssh.run(["pwd"])
            home_dir = pwd_result.stdout.strip()
            
            # Build the Docker image
            print("Building Docker image (this may take a while)...")
            build_cmd = f"""cd {home_dir}/SWELancer-Benchmark && docker buildx build -f Dockerfile_x86 --platform linux/amd64 -t {self.docker_image} . 2>&1"""
            
            print(f"Running build command: {build_cmd}")
            build_result = ssh.run(["bash", "-c", build_cmd], timeout=900)  # 15 minute timeout
            
            if build_result.exit_code != 0:
                # Try alternative approach
                print("First build attempt failed. Trying alternative approach...")
                alt_build_cmd = f"""
                pushd {home_dir}/SWELancer-Benchmark
                ls -la  # Check files
                docker buildx build -f ./Dockerfile_x86 -t {self.docker_image} .
                popd
                """
                alt_result = ssh.run(["bash", "-c", alt_build_cmd], timeout=900)
                
                if alt_result.exit_code != 0:
                    print("Both build attempts failed.")
                    raise RuntimeError("Failed to build Docker image")
            
            # Test the image
            print("Testing the built image...")
            test_result = ssh.run(["docker", "run", "--rm", self.docker_image, "echo", "Hello from SWE-Lancer container!"])
            print(f"Test output: {test_result.stdout}")
            
            # Save images list for verification
            images_result = ssh.run(["docker", "images"])
            print(f"Docker images available:\n{images_result.stdout}")
        
        # Create a snapshot with the built Docker image
        print("Creating snapshot with built Docker image...")
        snapshot = await instance.asnapshot()
        await snapshot.aset_metadata(self.swelancer_metadata)
        print(f"Snapshot created successfully with ID: {snapshot.id}")
    
    async def _ensure_base_snapshot(self) -> str:
        """Find or create a base snapshot with Docker installed"""
        # Check for existing snapshot with our metadata + the specific Docker image
        snapshots = await self.client.snapshots.alist(
            metadata={
                **self.base_snapshot_metadata,
                "docker_image": self.docker_image
            }
        )
        
        if snapshots:
            print(f"Found existing snapshot with Docker image: {self.docker_image}")
            return snapshots[0].id
        
        # No snapshot with this image, check for a base Docker snapshot
        snapshots = await self.client.snapshots.alist(
            metadata=self.base_snapshot_metadata
        )
        
        if snapshots:
            print("Found base Docker snapshot, will pull required image")
            snapshot_id = snapshots[0].id
        else:
            print("Creating new base snapshot with Docker")
            snapshot_id = await self._create_docker_base_snapshot()
            
        return snapshot_id
    
    async def _create_docker_base_snapshot(self) -> str:
        """Create a base snapshot with Docker installed"""
        
        # Create a snapshot with our resource specs
        snapshot = await self.client.snapshots.acreate(
            vcpus=self.resources["vcpus"],
            memory=self.resources["memory"],
            disk_size=self.resources["disk_size"]
        )
        
        # Start an instance
        instance = await self.client.instances.astart(snapshot.id)
        await instance.await_until_ready()
        
        try:
            # Use SSH to install Docker (more reliable than aexec)
            with instance.ssh() as ssh:
                print("Installing Docker via SSH...")
                
                # Update and install prerequisites
                ssh.run(["apt-get", "update"]).raise_on_error()
                ssh.run(["apt-get", "install", "-y", "curl", "apt-transport-https", 
                        "ca-certificates", "gnupg", "lsb-release"]).raise_on_error()
                
                # Install iptables-legacy which often resolves Docker issues
                ssh.run(["apt-get", "install", "-y", "iptables"]).raise_on_error()
                
                # Switch to iptables-legacy before installing Docker
                try:
                    ssh.run(["update-alternatives", "--set", "iptables", "/usr/sbin/iptables-legacy"]).raise_on_error()
                    ssh.run(["update-alternatives", "--set", "ip6tables", "/usr/sbin/ip6tables-legacy"]).raise_on_error()
                except Exception as e:
                    print(f"Note: Could not set iptables-legacy: {str(e)}")
                
                # Remove any existing Docker installation
                ssh.run(["apt-get", "remove", "--purge", "-y", "docker", "docker-engine", 
                         "docker.io", "containerd", "runc", "docker-ce", "docker-ce-cli", "containerd.io"])
                ssh.run(["apt-get", "autoremove", "-y"])
                ssh.run(["rm", "-rf", "/var/lib/docker", "/var/run/docker.sock"])
                
                # Install Docker using the official script
                ssh.run(["curl", "-fsSL", "https://get.docker.com", "-o", "install-docker.sh"]).raise_on_error()
                ssh.run(["sh", "install-docker.sh"]).raise_on_error()
                
                # Create Docker daemon configuration directory
                ssh.run(["mkdir", "-p", "/etc/docker"]).raise_on_error()

                # Create Docker daemon config file with proven working configuration
                daemon_config = '''{
                  "ipv6": false,
                  "ip6tables": false,
                  "experimental": false,
                  "log-driver": "json-file",
                  "log-opts": {
                    "max-size": "10m",
                    "max-file": "3"
                  },
                  "storage-driver": "overlay2"
                }'''
                
                ssh.run(["bash", "-c", f"echo '{daemon_config}' > /etc/docker/daemon.json"]).raise_on_error()
                
                # Reload systemd and restart Docker
                ssh.run(["systemctl", "daemon-reload"]).raise_on_error()
                ssh.run(["systemctl", "restart", "docker.service"]).raise_on_error()
                
                # Verify Docker is working by running hello-world
                print("Testing Docker with hello-world...")
                ssh.run(["docker", "run", "--rm", "hello-world"], timeout=30).raise_on_error()
                print("Docker verification succeeded!")
            
            # Create a new snapshot
            print("Creating snapshot with Docker installed")
            docker_snapshot = await instance.asnapshot()
            await docker_snapshot.aset_metadata(self.base_snapshot_metadata)
            
            return docker_snapshot.id
        finally:
            await instance.astop()

class MorphCloudValue:
    """Container for MorphCloud instance and container information"""
    def __init__(self, instance, container_name: str):
        self.instance = instance
        self.container_name = container_name

class MorphCloudInterface(ComputerInterface):
    """Implementation of ComputerInterface for MorphCloud"""
    def __init__(self, cluster_value: MorphCloudValue):
        self.cluster_value = cluster_value
   
    async def send_shell_command(
            self,
            cmd: str,
            timeout: int | None = None,
            user: str | None = None,
            container_id: int = 0,  # Ignored in MorphCloud implementation
            environment: dict[str, str] | None = None,
            workdir: str | None = None,
        ) -> ExecutionResult:
        """
        Not recommended. But for quick testing. It uses docker exec under the hood so directory changes aren't preserved.

        Args:
            cmd (str): Command to run
            timeout (int, optional): Timeout in seconds. Defaults to None.
            user (str, optional): User to run the command as. Defaults to None (root).
            container_id (int, optional): Ignored in MorphCloud implementation.
            environment (dict, optional): Environment variables.
            workdir (str, optional): Working directory.
        
        Returns:
            ExecutionResult: Object with output and exit_code
        """
        print(f'sending shell command: {cmd}')
        # Maintain the same validation logic from the original
        if not isinstance(cmd, str):
            raise ValueError(f"cmd must be of type string, but it was type {type(cmd)}")
        
        # For timeout validation, we'll assume a similar limit
        docker_client_timeout_seconds = 600  # Default value
        if hasattr(self, 'limits') and 'docker_client_timeout_seconds' in self.limits:
            docker_client_timeout_seconds = self.limits['docker_client_timeout_seconds']
            
        if timeout is not None and timeout >= docker_client_timeout_seconds:
            raise ValueError(f"{timeout=} must be less than {docker_client_timeout_seconds=} (which you can configure)")
        
        # Build the docker exec command exactly as it would be in the original implementation
        docker_cmd_parts = ["docker", "exec"]
        
        # Add options that match the original implementation
        if user is not None:
            docker_cmd_parts.extend(["-u", user])
        
        if workdir is not None:
            docker_cmd_parts.extend(["-w", workdir])
        
        # Add environment variables
        if environment is not None:
            for key, value in environment.items():
                docker_cmd_parts.extend(["-e", f"{key}={value}"])
        
        # Add container name
        docker_cmd_parts.append(self.cluster_value.container_name)
        
        # Add the command with timeout handling exactly as in original
        if timeout is None:
            docker_cmd_parts.extend(["sh", "-c", cmd])
        else:
            docker_cmd_parts.extend(["timeout", f"{timeout}s", "sh", "-c", cmd])
        
        # Execute the command using a single string to ensure it's passed correctly
        # We need to properly escape the components to handle spaces, quotes, etc.
        import shlex
        docker_cmd_str = " ".join(shlex.quote(part) for part in docker_cmd_parts)
        
        # Execute the command
        result = await self.cluster_value.instance.aexec(docker_cmd_str)
        
        # Process output to match exactly what the original would return
        # Ensure we handle both string and bytes correctly
        stdout: bytes
        if isinstance(result.stdout, bytes):
            stdout = result.stdout
        else:
            stdout = result.stdout.encode('utf-8') if result.stdout is not None else b''
        
        stderr: bytes
        if isinstance(result.stderr, bytes):
            stderr = result.stderr
        else:
            stderr = result.stderr.encode('utf-8') if result.stderr is not None else b''
        
        # Combine stdout and stderr as the original implementation would
        combined_output = stdout + (b"\n" if stdout and stderr else b"") + stderr
        
        # Log the output exactly as the original would
        if cmd != "cd /app/tests && zip -P 'secretpasswordhere' -r /app/tmp.zip . && mv /app/tmp.zip /app/tests.zip":
            print(f"cmd {cmd} -> ({result.exit_code}) {combined_output.decode('utf-8', errors='backslashreplace')}")
        
        # Return in the correct format for compatibility
        return ExecutionResult(
            output=combined_output,
            exit_code=result.exit_code
        )

    
    async def upload(self, file_data: bytes, destination: str) -> None:
        """Upload a file to the container"""
        # Create a temporary file on the VM
        temp_path = f"/tmp/upload_{uuid.uuid4().hex}"
        
        with self.cluster_value.instance.ssh() as ssh:
            # Write a temporary file via SFTP
            sftp = ssh._client.open_sftp()
            try:
                with sftp.open(temp_path, 'wb') as f:
                    f.write(file_data)
                
                # Copy to container - use the approach that worked in tests
                ssh.run(f"docker cp {temp_path} {self.cluster_value.container_name}:{destination}").raise_on_error()
                
                # Clean up temporary file
                ssh.run(f"rm {temp_path}")
            finally:
                sftp.close()
    
    async def download(self, file_path: str) -> bytes:
        """Download a file from the container"""
        # Create a temporary file on the VM
        temp_path = f"/tmp/download_{uuid.uuid4().hex}"
        
        with self.cluster_value.instance.ssh() as ssh:
            # Copy from container to VM - use the approach that worked in tests
            ssh.run(f"docker cp {self.cluster_value.container_name}:{file_path} {temp_path}").raise_on_error()
            
            # Read the file content using SFTP
            sftp = ssh._client.open_sftp()
            try:
                with sftp.open(temp_path, 'rb') as f:
                    file_data = f.read()
                
                # Clean up temporary file
                ssh.run(f"rm {temp_path}")
                
                return file_data
            finally:
                sftp.close()
    
    async def check_shell_command(self, command: str) -> ExecutionResult:
        """Execute a command and raise an error if it fails"""
        result = await self.send_shell_command(command)
        assert result.exit_code == 0, (
            f"Command {command} failed with {result.exit_code=}\n\n{safe_decode(result.output)}"
        )
        return result

        
    async def disable_internet(self) -> None:
        """Disable internet access for the container"""
        print("Disabling internet...")
        try:
            with self.cluster_value.instance.ssh() as ssh:
                # Get the container network config (subnet) - using approach from tests
                inspect_cmd = f"docker inspect {self.cluster_value.container_name} --format='{{{{.NetworkSettings.Networks.bridge.Subnet}}}}'"
                subnet_result = ssh.run(["bash", "-c", inspect_cmd])
                if subnet_result.exit_code != 0:
                    print(f"Warning: Failed to get subnet: {subnet_result.stderr}")
                    return
                
                subnet = subnet_result.stdout.strip().replace("'", "")
                
                # Block internet using iptables with the structure from tests.py
                cmd_template = """
                # Container network rules
                iptables -I DOCKER-USER 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
                iptables -I DOCKER-USER 2 -s {subnet} -d {subnet} -j ACCEPT
                iptables -I DOCKER-USER 3 -s {subnet} -j REJECT
                # Host communications
                iptables -I INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
                iptables -I INPUT 2 -s {subnet} -j REJECT
                """
                
                # Create a temporary script file
                script_path = f"/tmp/disable_net_{uuid.uuid4().hex}.sh"
                ssh.run(["bash", "-c", f"cat > {script_path} << 'EOL'\n{cmd_template.format(subnet=subnet)}\nEOL\n"])
                ssh.run(["chmod", "+x", script_path])
                
                # Execute the script
                ssh.run(["bash", script_path])
                
                # Clean up the temporary file
                ssh.run(["rm", script_path])
                
                # Verify the block works by checking if we can access the internet
                test_result = ssh.run([
                    "docker", "exec", self.cluster_value.container_name, 
                    "ping", "-c", "1", "-W", "3", "8.8.8.8"
                ])
                
                if test_result.exit_code == 0:
                    print("Warning: Network block might not be effective")
                else:
                    print("Internet access disabled successfully")
                    
        except Exception as e:
            print(f"Warning: Failed to disable internet: {str(e)}")
            # Don't raise the error, as this is not critical functionality
    
    async def fetch_container_names(self) -> List[str]:
        """Fetch all container names running in the instance"""
        try:
            # Just return the container name we already have, like in tests
            return [self.cluster_value.container_name]
        except Exception as e:
            print(f"Error fetching container names: {str(e)}")
            return []
    
    async def stop(self) -> None:
        """Stop the container using the approach from tests"""
        print(f"Shutting down {self.cluster_value.container_name}")
        try:
            # Stop and remove the container
            await self.cluster_value.instance.aexec(f"docker stop {self.cluster_value.container_name}")
            await self.cluster_value.instance.aexec(f"docker rm {self.cluster_value.container_name}")
        except Exception as e:
            print(f"Error stopping container: {str(e)}")
            # Don't raise as we want cleanup to continue

@chz.chz
class SimpleAgentSolver(PythonCodingSolver):
    name: str = "SimpleAgentSolver"
    model: str = "gpt-4o"

    def shortname(self) -> str:
        return "simple-solver"
    
    @asynccontextmanager
    async def _start_computer(self, task: ComputerTask) -> AsyncGenerator[ComputerInterface, None]:
        # Use our new MorphCloud-based implementation
        
        # print(f'TASK: {task}')
        morph_config = task_to_morph_config(task)
        
        # Set debugging flag - change to False in production
        debug_mode = True  # Set to True to keep instances running on error
        
        async with morph_config.build(cleanup_on_error=not debug_mode) as morph_value:
            yield MorphCloudInterface(cluster_value=morph_value)
    
    @asynccontextmanager
    async def _with_cached_setup(self, task: ComputerTask) -> AsyncGenerator[ComputerInterface, None]:
        """
        Higher-order function that either uses a cached snapshot or runs normal setup.
        Returns an async generator that yields a ready-to-use computer interface.
        """
        issue_id = task.environment.get("ISSUE_ID", "")
        force_setup = os.environ.get("FORCE_SETUP", "")
        
        if issue_id and not force_setup:
            # Check for existing snapshot
            client = MorphCloudClient(api_key=os.environ.get("MORPH_API_KEY"))
            snapshots = await client.snapshots.alist(
                metadata={
                    "purpose": "swelancer-task-ready",
                    "issue_id": issue_id,
                    "docker_image": task.docker_image
                }
            )
            
            if snapshots:
                print(f"{COLORS['GREEN']}Morph found existing snapshot {snapshots[0].id} for issue {issue_id}{COLORS['RESET']}")
                try:
                    # Start instance from snapshot
                    instance = await client.instances.astart(snapshots[0].id)
                    await instance.await_until_ready()
                    
                    # Extract container name from metadata (with fallback)
                    container_name = snapshots[0].metadata.get("container_name", f"swelancer-{uuid.uuid4().hex[:8]}")
                    
                    # Check if container exists (running or stopped)
                    container_exists = await instance.aexec(f"docker ps -a --filter name={container_name} --format '{{{{.Names}}}}'")
                    
                    if container_exists.stdout.strip():
                        # Container exists, check if it's running
                        is_running = await instance.aexec(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'")
                        
                        if not is_running.stdout.strip():
                            print(f"Container {container_name} exists but is not running, starting it")
                            start_result = await instance.aexec(f"docker start {container_name}")
                            if start_result.exit_code != 0:
                                print(f"Failed to start container: {safe_decode(start_result.stderr)}")
                                raise RuntimeError(f"Failed to start container {container_name}")
                    else:
                        # Container doesn't exist, we need to create it
                        print(f"Container {container_name} not found, creating new container")
                        # Start new container with current task environment
                        env_args = ' '.join([f'-e {shlex.quote(f"{key}={value}")}' for key, value in task.environment.items()])
                        network_mode = "host"

                        # stdin_open True -i
                        # tty True -t
                        # detach True -d

                        docker_run_cmd = f"""
                            docker run -d \
                              --name {container_name} \
                              -u 0 \
                              --privileged \
                              --network={network_mode} \
                              -i -t \
                              {env_args} \
                              {task.docker_image}
                            """

                        # docker_run_cmd = f"docker run -d --name {container_name} {env_args} {task.docker_image}"
                        
                        print(f'Creating container with {docker_run_cmd}')
                        run_result = await instance.aexec(docker_run_cmd)
                        if run_result.exit_code != 0:
                            print(f"Failed to create container: {safe_decode(run_result.stderr)}")
                            raise RuntimeError(f"Failed to create container with cmd: {docker_run_cmd}")
                    
                    # We now have a running container
                    computer = MorphCloudInterface(MorphCloudValue(instance, container_name))
                    
                    try:
                        # Yield the ready computer
                        yield computer
                    finally:
                        # Consistent cleanup
                        debug_mode = os.environ.get("DEBUG_MODE", "")
                        if not debug_mode:
                            try:
                                # Stop the container first
                                await instance.aexec(f"docker stop {container_name}")
                                print(f"Stopped container {container_name}")
                            except Exception as e:
                                print(f"Warning: Failed to stop container: {e}")
                            
                            print(f"Stopping instance {instance.id}")
                            await instance.astop()
                        else:
                            print(f"DEBUG MODE: Leaving instance {instance.id} and container {container_name} running")
                    
                    # Exit the generator after cleanup
                    return
                except Exception as e:
                    print(f"Error using cached snapshot: {e}. Falling back to normal setup.")
                    # Fall through to normal setup
        
        # If we get here, we need to do the normal setup
        print("No issue_id snapshot found, proceeding with normal setup")
        async with self._start_computer(task) as computer:
            # Run the task setup
            try:
                await task.setup(computer)
                
                # Create a snapshot after setup only if successful
                if isinstance(computer, MorphCloudInterface) and issue_id:
                    try:
                        print(f"Creating snapshot for issue {issue_id}")
                        snapshot = await computer.cluster_value.instance.asnapshot()
                        
                        # Consistent metadata
                        metadata = {
                            "purpose": "swelancer-task-ready",
                            "issue_id": issue_id,
                            "docker_image": task.docker_image,
                            "container_name": computer.cluster_value.container_name,
                            "created_at": str(int(time.time())),
                            "version": "1.0"  # For future compatibility
                        }
                        
                        await snapshot.aset_metadata(metadata)
                        print(f"Created snapshot {snapshot.id} for issue {issue_id}")
                    except Exception as e:
                        print(f"Warning: Failed to create snapshot: {e}")
            except Exception as e:
                print(f"Task setup failed: {e}")
                raise
            
            # Yield the computer after setup
            yield computer

    

    @override
    async def run(self, task: ComputerTask) -> AsyncGenerator[Step | FinalResult, None]:
        print(f"{COLORS['GREEN']}Running with MorphCloud!{COLORS['RESET']}")
        try:
            async with self._with_cached_setup(task) as computer:

                print(f"{COLORS['GREEN']}Agent Loop Started!{COLORS['RESET']}")
                # 2. Query the API / some agent
                messages = [] 
                for prompt_message in task.prompt:
                    messages.append({
                        "role": "user",
                        "content": str(prompt_message["content"]) # type: ignore
                    })
                messages.append({"role": "user", "content": """The repository is cloned in your CWD. You must send Python code in backticks in each response to me, and I will execute the code and send you back the result, for example:
                                                                       
```python
import os
print(os.listdir())
```

You can include other content in your message, as long as it has the Python code block. You must only submit one code block per message.
                                 
The python code block is your means of interactign with the environment; write Python code to view files, edit files, and run commands. Do not leave any steps incomplete. You must implement all fixes yourself.
                                                                       
When you are done, send "DONE" (and nothing else - you don't need a python code block), and we will grade your submission.
                                 
Please note that the Python code is not a Jupyter notebook; you must write a full Python script each time, including imports, and printing things if you want to see the output.
"""})
                max_turns = 30
                print(messages)

                loop_exit_reason = "Reached maximum number of turns"

                for remaining_turns in range(max_turns, 0, -1):
                    model_response = get_model_response(messages)
                    print(model_response)

                    messages.append({"role": "assistant", "content": model_response})

                    execution_output = None

                    # Check if model is done
                    if model_response.strip().lower() == "done":
                        print("Breaking because model is done!")
                        loop_exit_reason = "Model explicitly finished by sending 'DONE'"

                        break

                    # Check for user-tool calls
                    if "<user-tool>" in model_response:
                        print('User tool called.')
                        await computer.check_shell_command("unzip -q -P 'secretpasswordhere' /app/tests.zip -d /app/tests")
                        execution_output = await computer.check_shell_command("bash -c -i 'user-tool'")
                        print('User tool ran, with output:')
                        # print(execution_output)
                        execution_output = 'User tool output is in /app/expensify/user_tool'
                        await computer.send_shell_command(
                            "rm -rf /app/tests"
                        )
                        await computer.send_shell_command("rm -rf /app/tests")
                    else:
                        # Extract Python code from the model response
                        python_blocks = re.findall(r"```python\s*\n(.*?)\n```", model_response, re.DOTALL)

                        if not python_blocks:
                            messages.append({
                                "role": "user",
                                "content": "Warning: No Python code blocks were found in the response. Please include Python code in your replies."
                            })
                            continue

                        code = dedent(python_blocks[0])

                        execution_output = await computer.send_shell_command(f"python -c {shlex.quote(code)}")
                        execution_output = safe_decode(execution_output.output)

                    # print(execution_output)

                    # Append the code and its output to the messages
                    messages.append({
                        "role": "user",
                        "content": f"{execution_output}\nTurns left: {remaining_turns - 1}"
                    })

                # 3. Grade and yield the final result
                print(f"Agent loop exited: {loop_exit_reason}")
                grade = await task.grade(computer)
                yield FinalResultSuccessful(grade=grade)
        except Exception as e:
            print(f"Error: {e}")
            traceback_str = traceback.format_exc()
            yield FinalResultSuccessful(
            grade=Grade(score=0, grader_log=f"Grading failed with error: {str(e)}")
        )

