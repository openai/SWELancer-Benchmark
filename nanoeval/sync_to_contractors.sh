# Sync nanoeval and its monorepo dependencies to openai/alcatraz-dev. This
# repo is accessible by Tier II contractors only. This script should only be
# run manually and diffs carefully inspected before pushing + making a pull
# request in openai/alcatraz-dev.
#
# Signed off by:
# - @kevinliu - nanoeval
# - Ryan Ragona - Security approval for package transfer https://openai.slack.com/archives/C78H8DHNF/p1729096881201359?thread_ts=1729096831.024269&cid=C78H8DHNF

set -xeuo pipefail

# Define the source and destination directories
SOURCE_DIRS=(
    "$(oaipkg where nanoeval)"
)
DEST_DIR=~/code/minimono/project

# Ensure the destination directory exists
test -d "$DEST_DIR"

# Copy the contents from the source to the destination, deleting changes in the source directories if they exist
for SOURCE_DIR in "${SOURCE_DIRS[@]}"; do
    rsync -av --delete --progress --exclude 'pyproject.toml' "$SOURCE_DIR/" "$DEST_DIR/$(basename "$SOURCE_DIR")"
done
