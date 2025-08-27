import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Set, Any, Dict, Union


import requests
from github import Auth, Github

from patchstorm.config import GIT_NAME, GIT_EMAIL, GITHUB_PROJECT, GITHUB_TOKEN, ARTIFACTS_DIR
from tasks.celery import app

# Import RunAgentConfig class
import sys

from tasks.cmdline_utils import run_bash_cmd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from patchstorm.run_agent_config import RunAgentConfig


@app.task
def get_all_repositories(organization):
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)

    repos = g.get_organization(organization).get_repos()
    return [repo.name for repo in repos]

def _run_agent(config, repo_dir, run_id):
    # Use the first prompt in the list
    if not config.prompts:
        raise ValueError("No prompts provided in configuration")

    if len(config.prompts) > 1 and config.agent_provider == 'codex':
        raise NotImplementedError("Multiple prompts are not supported for codex yet. Please use only one prompt.")

    if config.agent_provider == 'claude_code':
        # generate script with all commands
        script = f"""#!/bin/bash
set -ex
claude --dangerously-skip-permissions --output-format stream-json --verbose -p "{config.prompts[0]}"
"""
        for cmd in config.prompts[1:]:
            script += f'claude --dangerously-skip-permissions --output-format stream-json --verbose -p --continue "{cmd}"\n'
        print(script)
        script_filename = f"{ARTIFACTS_DIR}/{run_id}_script.sh"
        with open(script_filename, 'w') as f:
            f.write(script)
        cmd = f"""docker run -v {repo_dir}:/repo -v {script_filename}:/claude_cmds.sh -e ANTHROPIC_API_KEY --workdir /repo --env-file /secrets/.env.custom claude_code bash /claude_cmds.sh"""
    elif config.agent_provider == 'codex':
        prompt = config.prompts[0]
        cmd = f"""docker run -t -v {repo_dir}:/repo --workdir /repo -e OPENAI_API_KEY codex "{prompt}" """
    print(cmd)
    output, _ = run_bash_cmd(cmd, log_cmd=True)
    return output


def _clone_repo(repo_name, repo_dir):
    run_bash_cmd(f"git clone https://oauth2:{GITHUB_TOKEN}@github.com/{repo_name}.git {repo_dir}")


@app.task
def clone_and_run_prompt(repo_name, config):
    # If config is a string (JSON), deserialize it
    if isinstance(config, str):
        config = RunAgentConfig.from_json(config)
    run_id = uuid.uuid4().hex
    print(f"beginning run {run_id}")
    repo_dir = f"{ARTIFACTS_DIR}/{repo_name}_{run_id}"
    _clone_repo(repo_name, repo_dir)

    # TODO: there is no quote escaping or anything
    print(config.prompts)
    for prompt in config.prompts:
        if '"' in prompt or "'" in prompt:
            raise NotImplementedError("Prompt contains quotes, which is not supported yet. Please remove them.")
    if "'" in config.commit_msg or '"' in config.commit_msg:
        raise NotImplementedError("Commit message contains quotes, which is not supported yet. Please remove them.")

    output = _run_agent(config, repo_dir, run_id)
    print(output)
    with open(f'{ARTIFACTS_DIR}/{run_id}_output.txt', 'w') as f:
        f.write(output)
    # at this point, the PR is done

    if config.agent_provider == 'codex':
        # codex does not return the cost or duration in the output
        # pulling this could be complicated. we also lack permissions
        # because usage costs are viewable only by openai platform org admins
        # which we cannot be granted at the moment
        stats = {
            'cost_usd': 'codex costs are currently unsupported',
            'duration_ms': 'codex duration is currently unsupported',
        }
    elif config.agent_provider == 'claude_code':
        metadata = output.split("\n")[-1]
        # start = output.rfind('{')
        # end = output.rfind('}') + 1
        # contains keys cost_usd duration_api_ms duration_ms role
        try:
            stats = json.loads(metadata)
        except json.JSONDecodeError as e:
            print(f"Failed to parse output: {e}")
            print(metadata)
            raise
        stats['cost_usd'] = round(stats['total_cost_usd'], 2)
    stats['agent'] = config.agent_provider

    branch = f"bot/{run_id}"
    run_bash_cmd(f"git -C {repo_dir} checkout -b {branch}")
    run_bash_cmd(f"git -C {repo_dir} add {repo_dir}")
    diff, status = run_bash_cmd(f"git -C {repo_dir} diff HEAD --exit-code", raise_on_error=False)
    print(f"diff: {diff}")
    if config.skip_pr:
        print("Skipping PR creation")
        return
    if status != 0:
        print("Diff found, committing changes")
        # TODO: there is no quote escaping or anything
        body = f"This is an AI generated PR.\n\nAgent: {stats['agent']}\nExecution time: {stats['duration_ms']} ms\nCost: ${stats['cost_usd']}"
        run_bash_cmd(f"git config --global user.email {GIT_EMAIL}")
        run_bash_cmd(f"git config --global user.name '{GIT_NAME}'")
        run_bash_cmd(f"git -C {repo_dir} commit -m '{config.commit_msg}'")
        run_bash_cmd(f"git -C {repo_dir} push origin {branch}")
        project = ''
        if GITHUB_PROJECT:
            project = f" --project '{GITHUB_PROJECT}'"
        
        # Add --draft flag only if config.draft is True
        draft_flag = "--draft" if config.draft else ""
        gh_cmd = f"""cd {repo_dir} && GITHUB_TOKEN={GITHUB_TOKEN} gh pr create --head  bot/{run_id} --title "{config.commit_msg}" {draft_flag} {project} --body '{body}' """
        if config.reviewers:
            gh_cmd += f" --reviewer {','.join(config.reviewers)}"
        run_bash_cmd(gh_cmd)
    else:
        print("No changes found")
    print(f"Completed run {run_id}")
