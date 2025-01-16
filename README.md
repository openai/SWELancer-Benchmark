# Running SWELancer 

**Step 1:** Build 
- Please run the command that corresponds to your computer's architecture. 

```
docker buildx build \
  -f Dockerfile \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer \
  .
```

```
  -f Dockerfile_x86 \
  --platform linux/amd64 \
  --ssh default=$SSH_AUTH_SOCK \
  -t swelancer_x86 \
  .
```

**Step 2:** Run the Container 

You'll need to set the environment variables defined in `sample.env`. The `ISSUE_ID` corresponds to the folder name the `issues` directory.
