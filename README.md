# Running Expensify Tests Inside Docker Environments

This README provides instructions for setting up and running Expensify tests inside a Docker environment. Follow these steps carefully to ensure successful configuration and execution.

## Steps to Set Up

1. **Install GitHub CLI and Authenticate via SSH**
   - Install GitHub CLI on your system:
     - **macOS**:
       ```bash
       brew install gh
       ```
     - **Ubuntu**:
       ```bash
       sudo apt update && sudo apt install gh -y
       ```
     - **Windows** (Inside WSL2, recommended):
       ```bash
       sudo apt update && sudo apt install gh -y
       ```
   - Authenticate GitHub CLI and set up SSH:
     ```bash
     gh auth login --git-protocol ssh
     ```
   - During the login process, GitHub CLI will prompt you to create an SSH key if one does not exist and add it to your GitHub account automatically.

2. **Install `openssh-client` and Configure SSH Agent**
   - Install the OpenSSH client to enable SSH connections (if not already installed):
     - **macOS**: OpenSSH is pre-installed.
     - **Ubuntu**:
       ```bash
       sudo apt install openssh-client -y
       ```
     - **Windows** (Inside WSL2):
       ```bash
       sudo apt install openssh-client -y
       ```

3. **Create the Docker Network**
   - Before starting, create a dedicated Docker network named `expensify-network` to ensure proper communication between containers:
     ```bash
     docker network create expensify-network
     ```

4. **Run Verdaccio for Caching**
   - Start the Verdaccio container for npm caching. Use the following command:
     ```bash
     docker run -it -d --name npmcache --network expensify-network -p 4873:4873 verdaccio/verdaccio
     ```

5. **Create the Required Structure**
   - Navigate to the `issues/` folder and create the necessary structure for your specific issue. Use the sample issue as a reference.
   - The following files are needed:
     - `test.py`
     - `flow.mitm`
     - `commit_id.txt`
     - `git_tag.txt`
     - `bug_reintroduce.patch`
   - You can use the `create.py` script to automatically set up the directory structure.

6. **Copy and Populate Environment Variables**
   - Create a copy of the `sample.env` file and rename it to `.env`.
   - Populate the `.env` file with the required variables, especially the Pusher Keys and Issue ID.

7. **Build the Docker Container**
   - Use the following command to build the Docker container and tag it as `expensify_replay`. Include the SSH socket parameter for proper access:
     ```bash
     eval "$(ssh-agent -s)"
     ssh-add ~/.ssh/id_ed25519
     docker buildx build --ssh default=$SSH_AUTH_SOCK -t expensify_replay .
     ```

8. **Run the Docker Container**
   - Run the Docker container using the following command and pass the environment file. Name the container `expdev`:
     ```bash
     docker run -it --rm --network expensify-network \
      -p 5900:5900 -p 5901:5901 \
      --name expdev \
      --env-file .env \
      -v "$(pwd)/issues:/app/tests/issues" \
      -v "$(pwd)/logs:/app/tests/logs" \
      -v "$(pwd)/attempts:/app/tests/attempts" \
      expensify_replay
     ```
   - This command will mount the `issues/` directory to the container and provide access to the test files. This allows you to modify the test files and run the updated tests inside the container for debugging purposes.

9. **Automatic Configuration**
   - The pre-start scripts for the container will automatically configure the Expensify Repo and mitmproxy. This includes installing certificates, generating root authority, installing Node, and setting up dependencies.

10. **Accessing the Bash Shell**
    - Once the setup is complete, you will land in a bash shell inside the Docker container.

11. **Accessing the VNC Interface via Browser**
    - The container is configured to provide a VNC interface through a browser. Follow these steps to access it:
      - Open your browser and navigate to:
        ```
        http://localhost:5901/vnc.html
        ```
      - Press the Connect button. You will see the graphical interface where you can interact with the tests or monitor the environment.

12. **Validating Tests**
    - To validate the broken state, run the following command:
      ```bash
      ansible-playbook -i "localhost," --connection=local run_broken_state.yml
      ```
    - To validate the fixed state, run the following command:
      ```bash
      ansible-playbook -i "localhost," --connection=local run_fixed_state.yml
      ```
    - Logs for debugging can be found in the `/app/tests/logs` directory.

## Conclusion

Follow these steps to successfully run Expensify tests inside a Docker environment. For any issues, check the logs or refer to the documentation for more details.
