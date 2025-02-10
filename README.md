# SWE-Lancer

This repo contains the dataset and code for the paper "SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?".

### Setup

**Step 0**: Install Packages

```bash
# Will install nanoeval, alcatraz, nanoeval_alcatraz in editable mode
uv sync
```

**Step 1:** Build the Docker Image

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
  -f Dockerfile_x86 \
  --platform linux/amd64 \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer_x86 \
  .
```

**Step 2:** Add credentials to your environment

- Set the environment variables in "Optional Settings" defined in `sample.env`. The `ISSUE_ID` corresponds to the folder name in the `issues` directory.
- Add Pusher key credentials to your `.env` file:
  - Make a Channel on https://dashboard.pusher.com/ (you'll need to sign in with Github or make an account first)
    - When making a channel, you'll be asked to provide an app name, cluster, and choose your tech stack. None of these matter for our purposes, so there's no need to change the defaults here. Just click "create app".
  - Then Click on App Keys in the sidebar -- it should show you your `key` and `secret`. Make sure the `key` is added to your `.env` file.

**Step 3:** Run the container and confirm tests work

- You can run the container by pressing the "Run" button within the Docker app.
- After running the docker container, please try to run the tests via `bash -i -c 'ansible-playbook /app/tests/run_user_tool.yml`. After letting that run, if you go to the "Files" section of the Docker container, you should see that there were were new attempt files and log files added.
