import os

base_path = '/Users/samuelgm/SWELancer-Benchmark/issues'

for folder_name in os.listdir(base_path):
    folder_path = os.path.join(base_path, folder_name)
    if os.path.isdir(folder_path):
        git_tag_path = os.path.join(folder_path, 'issue_introduction.patch')
        if not os.path.exists(git_tag_path):
            with open(git_tag_path, 'w') as f:
                pass