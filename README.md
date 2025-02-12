# SWE-Lancer

This repo contains the dataset and code for the paper "SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?".

**Step 1: Package Management and Requirements**

Python 3.11 is the most stable version to use with SWE-Lancer.

For package management, this repo comes with a pre-existing virtualenv or you can build one from scratch.

We recommend using the pre-built virtualenv with [uv](https://github.com/astral-sh/uv), a lightweight OSS package manager. To do this, run:

```bash
source .venv/bin/activate
pip install uv
uv sync
```

To use your own virtualenv, without uv, run:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
for proj in nanoeval alcatraz nanoeval_alcatraz; do
  uv pip install -e project/"$proj"
done
```

**Step 2: Build the Docker Image**

Please run the command that corresponds to your computer's architecture.

For Apple Silicon (or other ARM64 systems):

```bash
docker buildx build \
  -f Dockerfile \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer \
  .
```

For Intel-based Mac (or other x86_64 systems):

```bash
docker buildx build \
  -f Dockerfile_x86 \
  --platform linux/amd64 \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer_x86 \
  .
```

**Step 3: Configure Environment Variables**

Locate the `sample.env` file in the root directory. This file contains template environment variables needed for the application:

```plaintext
# sample.env contents example:
OPENAI_API_KEY=your-key-here
OPENAI_USER=your-username
PUSHER_APP_ID=your-app-id
# ... other variables
```

Create a new file named `.env` and copy the contents from `sample.env`. Fill in the appropriate values for each variable (you will get the values for the Pusher variables in the next step).

**Step 4: Set Up Pusher Integration**

We use Pusher as a real-time messaging service to handle communication between different components of our workflow. Pusher allows us to send notifications and updates between the LLM agent and the testing infrastructure. To set up Pusher:

1. Create an account at [Pusher](https://dashboard.pusher.com/) (you can sign in with GitHub).
2. Create a new Pusher channel:
   - Click "Create App" (default settings are fine).
   - Provide any app name.
   - Select a cluster (default is fine).
   - Choose any tech stack (it doesn't affect functionality).
3. Once created, click on "App Keys" in the sidebar.
4. Copy the following credentials to your `.env` file:
   - App ID
   - Key
   - Secret
   - Cluster

**Step 5: Run the container and confirm tests work**

You can run the container by pressing the "Run" button within the Docker app. After running the Docker container, verify the setup by connecting to your Docker container and running:

```bash
bash -i -c 'ansible-playbook /app/tests/run_user_tool.yml'
```

Check the "Files" section of the Docker container - you should see new attempt files and log files added.

**Step 6: Running SWE-Lancer**

You are now ready to run the eval with:

```bash
python run_swelancer.py
```

You should immediately see logging output as the container gets set up and the tasks are loaded, which may take several minutes. You can adjust the model, concurrency, recording, and other parameters in `run_swelancer.py`.