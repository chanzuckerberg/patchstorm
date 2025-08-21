#!/usr/bin/env python3
import time
import contextlib
import os
import re
import requests
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", 'localhost:11434')
MAX_LOG_FILE_READ_SIZE = 102400

github_mcp = FastMCP("patchstorm_mcp")


@github_mcp.tool()
def get_failing_workflow_logs_from_git_sha(owner: str, repo: str, git_sha: str) -> dict:
    """
    Extract failing workflow logs from a git sha. Useful if you don't have the PR URL but have the repo
    handy.

    First run this to get the owner and repo: git remote get-url origin
    To get the sha you can run git rev-parse HEAD

    Args:
        git_sha: git sha
        owner: Repository owner
        repo: Repository name

    Returns:
        list | dict: Contains failing workflow runs with their logs or a dict with an error key describing the issue.
    """
    try:
        # Set up GitHub API authentication
        headers = get_github_auth_headers()

        runs = get_workflow_runs_from_sha(owner, repo, git_sha, headers)

        # Filter for failing runs
        failing_runs = filter_failing_runs(runs)
        if not failing_runs:
            return {"message": "No failing workflow runs found for this PR."}

        # Get logs for each failing run
        result = extract_logs_for_failing_runs(owner, repo, failing_runs, headers)

        result = [summarize(entry) for entry in result]
        return result
    except Exception as e:
        return {"error": str(e)}


@github_mcp.tool()
def get_failing_workflow_logs_from_pr(pr_url: str) -> dict:
    """
    Extract failing workflow logs from a GitHub PR URL
    
    Args:
        pr_url: GitHub pull request URL (e.g., https://github.com/owner/repo/pull/123)
    
    Returns:
        list | dict: Contains failing workflow runs with their logs or a dict with an error key describing the issue.
    """
    try:
        # Parse PR URL
        owner, repo, pr_number = parse_github_pr_url(pr_url)

        # Set up GitHub API authentication
        headers = get_github_auth_headers()

        # Get workflow runs for this PR
        git_sha = get_head_sha_for_pr(owner, repo, pr_number, headers)
        return get_failing_workflow_logs_from_git_sha(owner, repo, git_sha)
    except Exception as e:
        return {"error": str(e)}

def summarize(entry: dict) -> dict:
    url = f"http://{OLLAMA_HOST}/api/chat"
    payload = {
        "model": "llama3.2",
        "messages": [
            {"role": "user", "content": f"You are the broker to an agentic coding agent. Find the relevant errors and print them out together with a summary of any issues or errors you see. Print error messages exactly. Print the name of all failing tests. Print stack traces. Print exceptions.\n\n{entry['logs']}"}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        entry['logs'] = response.json()["message"]["content"]
    except Exception as e:
        entry['logs'] = f"Error communicating with Ollama API: {str(e)}"

    return entry

def parse_github_pr_url(pr_url: str) -> tuple:
    """
    Parse a GitHub PR URL to extract owner, repo, and PR number
    
    Args:
        pr_url: GitHub pull request URL
        
    Returns:
        tuple: (owner, repo, pr_number)
        
    Raises:
        ValueError: If the URL is not a valid GitHub PR URL
    """
    pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, pr_url)
    
    if not match:
        raise ValueError("Invalid GitHub PR URL")
        
    owner = match.group(1)
    repo = match.group(2)
    pr_number = int(match.group(3))
    
    return owner, repo, pr_number

def get_github_auth_headers() -> dict:
    """
    Get GitHub API authentication headers using a personal access token
    
    Returns:
        dict: Headers for GitHub API requests
    
    Raises:
        ValueError: If GITHUB_TOKEN environment variable is not set
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token_file = os.environ.get("GITHUB_TOKEN_FILE")
        if token_file:
            with open(token_file, 'r') as f:
                token = f.read().strip()
    if not token:
        raise ValueError("neither GITHUB_TOKEN_FILE nor GITHUB_TOKEN environment variables are set")
        
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Workflow-Log-Extractor"
    }

def get_head_sha_for_pr(owner: str, repo: str, pr_number: int, headers: dict) -> str:
    """
    Get the head SHA for a specific PR

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        headers: GitHub API authentication headers

    Returns:
        str: Head SHA of the PR
    """
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    response = requests.get(pr_url, headers=headers)
    response.raise_for_status()
    pr_data = response.json()
    return pr_data["head"]["sha"]


def get_workflow_runs_from_sha(owner: str, repo: str, git_sha: str, headers: str) -> list:
    """
    Get workflow runs associated with a specific PR
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        headers: GitHub API authentication headers

    Returns:
        list: Workflow runs associated with the PR
    """
    # Now get workflow runs for this SHA
    runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs?head_sha={git_sha}"
    response = requests.get(runs_url, headers=headers)
    response.raise_for_status()
    
    return response.json().get("workflow_runs", [])

def filter_failing_runs(runs: list) -> list:
    """
    Filter workflow runs to include only failing ones
    
    Args:
        runs: List of workflow runs
        
    Returns:
        list: Failing workflow runs
    """
    return [run for run in runs if run.get("conclusion") == "failure"]

def extract_logs_for_failing_runs(owner: str, repo: str, failing_runs: list, headers: dict) -> list[dict]:
    """
    Extract logs for failing workflow runs
    
    Args:
        owner: Repository owner
        repo: Repository name
        failing_runs: List of failing workflow runs
        headers: GitHub API authentication headers
        
    Returns:
        dict: Structured results with failing runs and their logs
    """
    import io
    import zipfile
    
    result = []
    
    for run in failing_runs:
        run_id = run["id"]
        
        # Get log download URL
        logs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        response = requests.get(logs_url, headers=headers, allow_redirects=False)
        
        logs_content = {}
        if response.status_code == 302:
            # GitHub returns a redirect to the actual logs
            download_url = response.headers.get("Location")
            log_response = requests.get(download_url)
            
            if log_response.status_code == 200:
                # Logs are returned as a ZIP file
                try:
                    # Process the ZIP file
                    zip_data = io.BytesIO(log_response.content)
                    with zipfile.ZipFile(zip_data) as zip_file:
                        # Extract each file in the ZIP
                        for file_name in zip_file.namelist():
                            with zip_file.open(file_name) as log_file:
                                # Skip very large log files to prevent memory issues
                                # Read up to 100KB per log file
                                log_content = log_file.read(102400).decode('utf-8', errors='replace')
                                logs_content[file_name] = log_content
                except Exception as e:
                    logs_content["error"] = f"Failed to process logs: {str(e)}"
        
        result.append({
            "run_id": run_id,
            "workflow_name": run.get("name", "Unknown"),
            "created_at": run.get("created_at"),
            "html_url": run.get("html_url"),
            "logs": logs_content
        })
        
    return result

app = github_mcp.streamable_http_app()   # this serves the MCP endpoint

if __name__ == "__main__":
    # Expose the Streamable HTTP ASGI app and run it on all interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
