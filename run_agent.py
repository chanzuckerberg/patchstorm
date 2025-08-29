import argparse
import sys
from pathlib import Path

from tasks.celery import app
from tasks.github_tasks import (
    clone_and_run_prompt,
)
from patchstorm.run_agent_config import RunAgentConfig
from patchstorm.task_definition import validate_task_definition_yaml, SCHEMA
from patchstorm.github_utils import get_repos, get_repo_prs
import yaml


def load_task_definition(file_path):
    """
    Load and validate a task definition from a YAML file.
    
    Args:
        file_path (str): Path to the YAML file.
        
    Returns:
        dict: The validated task definition.
        
    Raises:
        ValueError: If the file cannot be read or is invalid.
    """
    with open(file_path, 'r') as f:
        yaml_content = f.read()
    return _load_task_definition_from_str(yaml_content)


def _load_task_definition_from_str(yaml_content):
    try:
        if validate_task_definition_yaml(yaml_content):
            return yaml.safe_load(yaml_content)
    except FileNotFoundError:
        raise ValueError(f"Task definition file not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error loading task definition: {str(e)}")


def create_config_from_task_definition(task_def, repos=None, search_query=None, dry=None, skip_pr=None, reviewers=None, draft=None) -> RunAgentConfig:
    """
    Create a RunAgentConfig from a task definition dictionary.
    
    Args:
        task_def (dict): The task definition dictionary.
        repos (str, optional): A comma-separated list of repos to run against.
        search_query (str, optional): Search query to find repos.
        dry (bool, optional): Force dry run mode. Overrides task definition if True.
        skip_pr (bool, optional): Skip creating PR. Overrides task definition if True.
        reviewers (str, optional): Comma-separated list of GitHub usernames to add as reviewers.
        draft (bool, optional): Whether to create PRs as drafts. Overrides task definition if provided.
        
    Returns:
        RunAgentConfig: The configuration object.
        
    Raises:
        ValueError: If the task definition is missing required fields.
    """
    if 'agent' not in task_def or 'provider' not in task_def['agent']:
        raise ValueError("Task definition must include agent.provider")
        
    if 'commit' not in task_def or 'message' not in task_def['commit']:
        raise ValueError("Task definition must include commit.message")
        
    if 'prompts' not in task_def or not task_def['prompts'] or 'prompt' not in task_def['prompts'][0]:
        raise ValueError("Task definition must include at least one prompt")
    
    # Check if repos or search_query are defined in the task definition
    task_repos_obj = task_def.get('repos')
    task_search_query = task_def.get('search_query')
    
    # Both repos and search_query can now be provided together
    # They will be combined in the get_repos function

    # Extract repos configuration from object format
    task_repos_list = None
    task_repos_search_query = None
    
    # Handle repos object format
    if task_repos_obj is not None:
        # Ensure repos is an object
        if not isinstance(task_repos_obj, dict):
            raise ValueError("'repos' must be an object with 'include' and/or 'search_query' properties")
        
        # Extract repositories from the object
        task_repos_list = task_repos_obj.get('include')
        task_repos_search_query = task_repos_obj.get('search_query')

    # Check for conflicting search queries
    if task_repos_search_query and task_search_query:
        raise NotImplementedError("Cannot specify both 'repos.search_query' and top-level 'search_query' in the task definition")
    
    # If both repos.include and repos.search_query are provided, that's fine - they're combined
    
    # Command line parameters take precedence over task definition
    if repos:
        repo_set = get_repos(repos, None)
    elif search_query:
        repo_set = get_repos(None, search_query)
    else:
        # Initialize repo_set with repos from include if available
        repo_set = set(task_repos_list) if task_repos_list else set()
        
        # Add repos from search query if available
        effective_search_query = task_repos_search_query or task_search_query
        if effective_search_query:
            search_results = get_repos(None, effective_search_query)
            # Union the sets to combine repositories from both sources
            repo_set = repo_set.union(search_results)
            
        # Ensure we have at least one source of repositories
        if not repo_set:
            raise ValueError("You must specify either repos.include, repos.search_query, or search_query in the task definition or as a command line argument.")
    
    # Command line flags take precedence over task definition
    use_dry = dry if dry is not None else task_def.get('dry', False)
    use_skip_pr = skip_pr if skip_pr is not None else task_def.get('skip_pr', False)
    use_draft = draft if draft is not None else task_def.get('draft', False)
    
    # Handle reviewers
    reviewers_set = set()
    if reviewers:
        reviewers_set = {r.strip() for r in reviewers.split(',')}
    elif 'reviewers' in task_def:
        reviewers_set = set(task_def['reviewers'])
    
    # Extract all prompts from the task definition
    prompts = [p['prompt'] for p in task_def['prompts'] if 'prompt' in p]
    
    return RunAgentConfig(
        commit_msg=task_def['commit']['message'],
        prompts=prompts,
        agent_provider=task_def['agent']['provider'],
        repos=repo_set,
        skip_pr=use_skip_pr,
        dry=use_dry,
        reviewers=reviewers_set,
        draft=use_draft
    )




def get_task_definition_from_stdin():
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def get_prompt_from_args(args):
    prompt = args.prompt
    if not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read()

    if not prompt:
        raise ValueError("You must pass a prompt with --prompt or via stdin")
        
    return prompt


def create_config_from_args(args):
    """Create a RunAgentConfig object from command line arguments."""
    if not args.skip_pr and not args.commit_msg:
        raise ValueError("You must provide a commit message with --commit-msg")
    
    repos = get_repos(args.repos, args.search_query)
    reviewers = set()
    if args.reviewers:
        reviewers = {r.strip() for r in args.reviewers.split(',')}

    return RunAgentConfig(
        commit_msg=args.commit_msg,
        prompts=[args.prompt],  # Convert single prompt to a list
        agent_provider=args.agent_provider,
        reviewers=reviewers,
        repos=repos,
        skip_pr=args.skip_pr,
        dry=args.dry,
        draft=args.draft if args.draft is not None else False
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-definition', type=str,
                        help='Path to a YAML file containing task definition')
    parser.add_argument('--commit-msg', type=str,
                        help='The commit message for the operation.')
    parser.add_argument('--prompt', type=str,
                        help='The prompt to give the llm.')
    parser.add_argument('--repos', type=str,
                        help='comma separated list of repos to run against, e.g. mygithuborg/myrepo,mygithuborg/myotherrepo')
    parser.add_argument('--search-query', type=str, default=None,
                        help="run on all repos that have this github code search query, eg --repo-query 'path:.github language:YAML tibdex/github-app-token'")
    parser.add_argument("--dry", action="store_true", help="Dry run, do not actually run the task")
    parser.add_argument("--skip-pr", action="store_true", help="Skip pushing and creating a pull request")
    parser.add_argument("--draft", action="store_true", help="Create pull request as draft. Defaults to false.")
    parser.add_argument("--agent-provider", choices=("codex", "claude_code"), default="codex",
                        help="Which agent to use for the task. Defaults to codex.")
    parser.add_argument("--reviewers", type=str, default="",
                        help="Comma separated list of GitHub usernames to add as reviewers to the PR.")
    parser.set_defaults(draft=None)

    args = parser.parse_args()
    
    try:
        if args.task_definition:
            task_def = load_task_definition(args.task_definition)
            
            config = create_config_from_task_definition(
                task_def, 
                repos=args.repos, 
                search_query=args.search_query,
                dry=args.dry,
                skip_pr=args.skip_pr,
                reviewers=args.reviewers,
                draft=args.draft
            )
        elif args.prompt:
            config = create_config_from_args(args)
        else:
            task_def = _load_task_definition_from_str(get_task_definition_from_stdin())
            if not task_def:
                parser.error("You must provide a task definition file or a prompt.")
            config = create_config_from_task_definition(
                task_def,
                repos=args.repos,
                search_query=args.search_query,
                dry=args.dry,
                skip_pr=args.skip_pr,
                reviewers=args.reviewers,
                draft=args.draft
            )
    except ValueError as e:
        parser.error(str(e))

    if config.dry:
        print(f"would run with prompts: {config.prompts}")
        print(f"commit message: {config.commit_msg}")
        print(f"reviewers: {config.reviewers}")
        print(f"agent provider: {config.agent_provider}")
        print(f"skip PR: {config.skip_pr}")

    filtered_repos = set()
    for repo in config.repos:
        if config.commit_msg in {pr.title for pr in get_repo_prs(repo)}:
            if config.dry:
                print(f"Skipping {repo} because a PR already exists.")
            continue
        filtered_repos.add(repo)

    print(f"running against {len(filtered_repos)} repo(s):")
    for repo in filtered_repos:
        print(f"  {repo}")

    for repo in filtered_repos:
        if config.dry:
            print(f"Would run on {repo}")
            continue
        clone_and_run_prompt.delay(repo, config.to_json())

    print("Tasks submitted. Run make logs-worker to check agent logs")
