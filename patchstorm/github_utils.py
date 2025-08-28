import os
import time
from github import Github
from github import Auth
from typing import Dict, List

from patchstorm.config import GITHUB_ORGANIZATION, GITHUB_TOKEN


def get_repos(repos=None, search_query=None):
    """
    Get repositories based on repo name or search query.
    
    Args:
        repos (str, optional): A specific repo to run against (comma-separated).
        search_query (str, optional): Search query to find repos.
        
    Returns:
        set: Set of repository names.
        
    Raises:
        ValueError: If neither repos nor search_query is provided.
    """
    result_repos = set()
    
    # Handle repos parameter if provided
    if repos:
        # Convert comma-separated string to set of repo names
        result_repos.update({r.strip() for r in repos.split(',')})
    
    # Handle search_query parameter if provided
    if search_query:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)

        paginated = g.search_code(f'org:{GITHUB_ORGANIZATION} {search_query} NOT is:archived')
        print(f"Processing {paginated.totalCount} repo results")
        for i, page in enumerate(paginated):
            result_repos.add(page.repository.full_name)
            time.sleep(0.2)
            if not i % 25:
                print(f"{i / paginated.totalCount:.2%} done")
    
    if not result_repos:
        raise ValueError("No repositories found with the provided repos or search_query parameters.")
        
    return result_repos


def get_repo_prs(repo_name: str) -> List:
    """
    Fetch all open and draft PRs for a given repository.
    """
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    # has attributes like number, title, url, draft
    return repo.get_pulls(state='open')
