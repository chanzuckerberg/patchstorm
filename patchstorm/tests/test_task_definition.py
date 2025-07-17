import pytest
import unittest.mock as mock
from patchstorm.task_definition import validate_task_definition_yaml
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from run_agent import create_config_from_task_definition, get_repos
from patchstorm.run_agent_config import RunAgentConfig


def test_valid_task_definition():
    assert True == validate_task_definition_yaml("""
    agent: 
        provider: codex
    commit:
        message: "Test commit message"
    prompts:
        - prompt: "Test prompt"
    """)


def test_valid_task_definition_with_repos():
    """Test that a task definition with repos is validated correctly."""
    assert True == validate_task_definition_yaml("""
    agent: 
        provider: codex
    commit:
        message: "Test commit message"
    prompts:
        - prompt: "Test prompt"
    repos:
        - mygithuborg/repo1
        - mygithuborg/repo2
    """)


def test_valid_task_definition_with_search_query():
    """Test that a task definition with search_query is validated correctly."""
    assert True == validate_task_definition_yaml("""
    agent: 
        provider: codex
    commit:
        message: "Test commit message"
    prompts:
        - prompt: "Test prompt"
    search_query: "path:.github language:YAML"
    """)


def test_valid_task_definition_with_draft():
    """Test that a task definition with draft is validated correctly."""
    assert True == validate_task_definition_yaml("""
    agent: 
        provider: codex
    commit:
        message: "Test commit message"
    prompts:
        - prompt: "Test prompt"
    draft: true
    """)


def test_invalid_agent_provider():
    """Test that an invalid agent provider is rejected."""
    with pytest.raises(ValueError) as excinfo:
        validate_task_definition_yaml("""
        agent: 
            provider: invalid_provider
        commit:
            message: "Test commit message"
        prompts:
            - prompt: "Test prompt"
        """)
    assert "YAML validation error" in str(excinfo.value)


def test_missing_prompt():
    """Test that a missing prompt is rejected."""
    with pytest.raises(ValueError) as excinfo:
        validate_task_definition_yaml("""
        agent: 
            provider: codex
        commit:
            message: "Test commit message"
        prompts:
            - not_prompt: "Test prompt"
        """)
    assert "YAML validation error" in str(excinfo.value)


def test_missing_commit_message():
    """Test that a missing commit message is rejected."""
    with pytest.raises(ValueError) as excinfo:
        validate_task_definition_yaml("""
        agent: 
            provider: codex
        commit:
            not_message: "Test commit message"
        prompts:
            - prompt: "Test prompt"
        """)
    assert "YAML validation error" in str(excinfo.value)


@mock.patch('run_agent.get_repos')
def test_convert_task_def_to_config(mock_get_repos):
    """Test converting a task definition to RunAgentConfig."""
    # Setup mock to return a set of repos
    mock_get_repos.return_value = {"test/repo", "another/repo"}
    
    task_def = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "repos": ["default/repo"]
    }
    
    config = create_config_from_task_definition(task_def, repos="test/repo,another/repo")
    
    assert isinstance(config, RunAgentConfig)
    assert config.commit_msg == "Test commit message"
    assert config.prompts == ["Test prompt"]
    assert config.agent_provider == "codex"
    assert config.repos == {"test/repo", "another/repo"}
    assert not config.skip_pr
    assert not config.dry
    assert not config.draft  # Default is False
    mock_get_repos.assert_called_with("test/repo,another/repo", None)


@mock.patch('run_agent.get_repos')
def test_convert_task_def_with_repos_to_config(mock_get_repos):
    """Test that repos defined in task definition are used in RunAgentConfig."""
    # Setup mock to return test repos
    mock_get_repos.side_effect = lambda repos, search_query: {r.strip() for r in repos.split(',')} if repos else set()
    
    task_def = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "repos": [
            "mygithuborg/repo1",
            "mygithuborg/repo2"
        ]
    }

    # without specifying repo parameter, repos from task definition should be used
    config = create_config_from_task_definition(task_def)

    assert isinstance(config, RunAgentConfig)
    assert config.repos == {"mygithuborg/repo1", "mygithuborg/repo2"}

    # repos parameter is specified, should override repos from task definition
    config_override = create_config_from_task_definition(task_def, repos="test/override")
    assert config_override.repos == {"test/override"}
    mock_get_repos.assert_called_with("test/override", None)


@mock.patch('run_agent.get_repos')
def test_convert_task_def_with_search_query_to_config(mock_get_repos):
    """Test that search_query defined in task definition is used in RunAgentConfig."""
    # Setup mock to return a set of repos
    mock_get_repos.return_value = {"found/repo1", "found/repo2"}
    
    task_def = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "search_query": "path:.github language:YAML"
    }
    
    # Test with task definition search_query
    config = create_config_from_task_definition(task_def)
    assert isinstance(config, RunAgentConfig)
    assert config.repos == {"found/repo1", "found/repo2"}
    mock_get_repos.assert_called_with(None, "path:.github language:YAML")
    
    # Test with command line search_query override
    config = create_config_from_task_definition(task_def, search_query="override:query")
    assert config.repos == {"found/repo1", "found/repo2"}
    mock_get_repos.assert_called_with(None, "override:query")


@mock.patch('run_agent.get_repos')
def test_convert_task_def_with_draft_to_config(mock_get_repos):
    """Test that draft defined in task definition is used in RunAgentConfig."""
    # Setup mock to return a set of repos
    mock_get_repos.return_value = {"test/repo"}
    
    # Test with draft=true in task definition
    task_def_with_draft = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "repos": ["test/repo"],
        "draft": True
    }
    
    config = create_config_from_task_definition(task_def_with_draft)
    assert isinstance(config, RunAgentConfig)
    assert config.draft is True
    
    # Test with draft=false in task definition
    task_def_without_draft = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "repos": ["test/repo"],
        "draft": False
    }
    
    config = create_config_from_task_definition(task_def_without_draft)
    assert isinstance(config, RunAgentConfig)
    assert config.draft is False
    
    # Test with draft param overriding task definition
    config = create_config_from_task_definition(task_def_without_draft, draft=True)
    assert config.draft is True
    
    config = create_config_from_task_definition(task_def_with_draft, draft=False)
    assert config.draft is False


def test_task_def_with_both_repos_and_search_query():
    """Test that specifying both repos and search_query raises NotImplementedError."""
    task_def = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ],
        "repos": ["mygithuborg/repo1"],
        "search_query": "path:.github language:YAML"
    }
    
    with pytest.raises(NotImplementedError) as excinfo:
        create_config_from_task_definition(task_def)
    assert "Cannot specify both 'repos' and 'search_query'" in str(excinfo.value)


def test_task_def_missing_required_fields():
    # Missing agent provider
    task_def1 = {
        "commit": {
            "message": "Test commit message"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ]
    }
    
    with pytest.raises(ValueError) as excinfo:
        create_config_from_task_definition(task_def1, repos="test/repo")
    assert "agent.provider" in str(excinfo.value)
    
    # Missing commit message
    task_def2 = {
        "agent": {
            "provider": "codex"
        },
        "prompts": [
            {
                "prompt": "Test prompt"
            }
        ]
    }
    
    with pytest.raises(ValueError) as excinfo:
        create_config_from_task_definition(task_def2, repos="test/repo")
    assert "commit.message" in str(excinfo.value)
    
    # Missing prompt
    task_def3 = {
        "agent": {
            "provider": "codex"
        },
        "commit": {
            "message": "Test commit message"
        }
    }
    
    with pytest.raises(ValueError) as excinfo:
        create_config_from_task_definition(task_def3, repos="test/repo")
    assert "prompt" in str(excinfo.value)