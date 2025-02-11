# SWE-Lancer 

This repo contains the dataset and code for the paper "SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?".

### Setup
**Step 1:** Verify Docker Installation
- Before starting, ensure Docker is properly installed on your system:
  ```bash
  docker --version
  ```
- If you don't see a version number, please install Docker Desktop from https://www.docker.com/products/docker-desktop
- After installation, verify Docker is running:
  ```bash
  docker ps
  ```
  This should show a list of running containers (might be empty if none are running)

**Step 2:** Build the Docker Image
- Please run the command that corresponds to your computer's architecture. 

For Apple Silicon (arm64):
```
docker buildx build \
  -f Dockerfile \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer \
  .
```

For Intel-based Mac (x86_64):
```
docker buildx build \
  -f Dockerfile_x86 \
  --platform linux/amd64 \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer_x86 \
  .
```

**Step 3:** Configure Environment Variables
- Locate the `sample.env` file in the root directory. This file contains template environment variables needed for the application:
  ```
  # sample.env contents example:
  ISSUE_ID=123
  OPENAI_API_KEY=your-key-here
  PUSHER_APP_ID=your-app-id
  # ... other variables
  ```
- Create a new file named `.env` and copy the contents from `sample.env`
- Fill in the values for each variable:
  - `ISSUE_ID`: This corresponds to the folder name in the `issues` directory you want to work with

**Step 4:** Set Up Pusher Integration
- We use Pusher as a real-time messaging service to handle communication between different components of our workflow
- Pusher allows us to send notifications and updates between the LLM agent and the testing infrastructure
- To set up Pusher:
  1. Create an account at https://dashboard.pusher.com/ (you can sign in with GitHub)
  2. Create a new Pusher channel:
     - Click "Create App" (default settings are fine)
     - Provide any app name
     - Select a cluster (default is fine)
     - Choose any tech stack (it doesn't affect functionality)
  3. Once created, click on "App Keys" in the sidebar
  4. Copy the following credentials to your `.env` file:
     - App ID
     - Key
     - Secret
     - Cluster

**Step 5:** Run the container and confirm tests work
- You can run the container by pressing the "Run" button within the Docker app
- After running the docker container, verify the setup by running the tests:
  ```bash
  bash -i -c 'ansible-playbook /app/tests/run_user_tool.yml'
  ```
- Check the "Files" section of the Docker container - you should see new attempt files and log files added
