import os
import re
import requests

def fetch_issue(issue_number):
    url = f"https://api.github.com/repos/Expensify/App/issues/{issue_number}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ExpensifyVideoDownloader"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching issue {issue_number}: {e}")
        return None

def download_issue_videos(issue):
    title = issue.get('title', '<No Title>')
    body = issue.get('body', '')
    
    print("Issue Title:", title)
    print("Issue Body:", body)

    video_urls = re.findall(r'(https?://[^\s]+?\.(?:mp4|mov))', body)
    if not video_urls:
        print("No .mp4 or .mov files found in the issue body.")
        return

    issue_id = str(issue.get('number') or issue.get('id', 'unknown'))
    destination_dir = os.path.join("issue_videos", issue_id)
    os.makedirs(destination_dir, exist_ok=True)

    for url in video_urls:
        video_name = os.path.basename(url.split('?')[0])
        destination_path = os.path.join(destination_dir, video_name)
        print(f"Downloading {url} to {destination_path} ...")

        try:
            video_response = requests.get(url, stream=True)
            video_response.raise_for_status()
            with open(destination_path, 'wb') as out_file:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        out_file.write(chunk)
            print(f"Downloaded {video_name} successfully.")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

def fetch_and_download_issue_videos(issue_number):
    issue = fetch_issue(issue_number)
    if issue is not None:
        download_issue_videos(issue)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python utils/download_videos.py <issue_number>")
    else:
        issue_number = sys.argv[1]
        fetch_and_download_issue_videos(issue_number)
