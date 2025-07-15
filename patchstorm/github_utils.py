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
        repo (str, optional): A specific repo to run against.
        search_query (str, optional): Search query to find repos.
        
    Returns:
        set: Set of repository names.
        
    Raises:
        ValueError: If neither repo nor search_query is provided.
    """
    if repos is None:
        repos = set()
    if search_query:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)

        paginated = g.search_code(f'org:{GITHUB_ORGANIZATION} {search_query} NOT is:archived')
        print(f"Processing {paginated.totalCount} repo results")
        for i, page in enumerate(paginated):
            repos.add(page.repository.full_name)
            time.sleep(0.2)
            if not i % 25:
                print(f"{i / paginated.totalCount:.2%} done")
    elif repos:
        repos = {r.strip() for r in repos.split(',')}
    else:
        raise ValueError("You must specify either repos or search_query.")

    return repos


def get_repo_prs(repo_name: str) -> List:
    """
    Fetch all open and draft PRs for a given repository.
    """
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    # has attributes like number, title, url, draft
    return repo.get_pulls(state='open')
