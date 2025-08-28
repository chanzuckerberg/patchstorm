import pytest
import unittest.mock as mock
import warnings
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


def test_valid_task_definition_with_repos_new_format():
    """Test that a task definition with repos in new format is validated correctly."""
    assert True == validate_task_definition_yaml("""
    agent: 
        provider: codex
    commit:
        message: "Test commit message"
    prompts:
        - prompt: "Test prompt"
    repos:
        include:
            - chanzuckerberg/patchstorm
            - chanzuckerberg/fogg
        search_query: '"set up working directory by installing dependencies" 0.92.2'
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
    """Test converting a task definition to RunAgentConfig and test include/search_query union."""
    # Setup mock with different results for different search queries
    def mock_get_repos_side_effect(repos, search_query):
        if repos == "test/repo,another/repo":
            return {"test/repo", "another/repo"}
        elif search_query == "path:.github language:YAML":
            return {"search/repo1", "search/repo2"}
        return set()
    
    mock_get_repos.side_effect = mock_get_repos_side_effect
    
    # First test with command line override
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
        "repos": {
            "include": ["include/repo1", "include/repo2"],
            "search_query": "path:.github language:YAML"
        }
    }
    
    config = create_config_from_task_definition(task_def, repos="test/repo,another/repo")
    
    assert isinstance(config, RunAgentConfig)
    assert config.commit_msg == "Test commit message"
    assert config.prompts == ["Test prompt"]
    assert config.agent_provider == "codex"
    # Command line parameters take precedence
    assert config.repos == {"test/repo", "another/repo"}
    assert not config.skip_pr
    assert not config.dry
    assert not config.draft  # Default is False
    mock_get_repos.assert_called_with("test/repo,another/repo", None)
    
    # Now test the union behavior with both include and search_query
    config = create_config_from_task_definition(task_def)
    
    assert isinstance(config, RunAgentConfig)
    # Should be the union of repos from include and search_query
    expected_repos = {"include/repo1", "include/repo2", "search/repo1", "search/repo2"}
    assert config.repos == expected_repos
    mock_get_repos.assert_called_with(None, "path:.github language:YAML")


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
def test_convert_task_def_with_combined_repos_and_top_level_search_query(mock_get_repos):
    """Test that repositories from include are combined with those found by top-level search_query."""
    # Setup mock for different search query results
    def mock_get_repos_side_effect(repos, search_query):
        if search_query == "path:.github language:YAML":
            return {"found/repo1", "found/repo2"}
        return set()
    
    mock_get_repos.side_effect = mock_get_repos_side_effect
    
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
        "repos": {
            "include": [
                "chanzuckerberg/patchstorm",
                "chanzuckerberg/fogg"
            ]
        },
        "search_query": "path:.github language:YAML"
    }
    
    # Test combining repos from include and top-level search_query
    config = create_config_from_task_definition(task_def)
    assert isinstance(config, RunAgentConfig)
    # Should combine repositories from include and search_query
    expected_repos = {"chanzuckerberg/patchstorm", "chanzuckerberg/fogg", "found/repo1", "found/repo2"}
    assert config.repos == expected_repos
    mock_get_repos.assert_called_with(None, "path:.github language:YAML")


@mock.patch('run_agent.get_repos')
def test_convert_task_def_with_repos_new_format_to_config(mock_get_repos):
    """Test that repos defined in new format are used in RunAgentConfig."""
    # Setup mock to return test repos for include list and search query results
    mock_repos_from_query = {"found/repo1", "found/repo2"}
    
    def mock_get_repos_side_effect(repos, search_query):
        if repos:
            return {r.strip() for r in repos.split(',')}
        elif search_query:
            return mock_repos_from_query
        return set()
    
    mock_get_repos.side_effect = mock_get_repos_side_effect
    
    # Test with include list only
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
        "repos": {
            "include": [
                "chanzuckerberg/patchstorm",
                "chanzuckerberg/fogg"
            ]
        }
    }
    
    config = create_config_from_task_definition(task_def)
    assert isinstance(config, RunAgentConfig)
    assert config.repos == {"chanzuckerberg/patchstorm", "chanzuckerberg/fogg"}
    
    # Test with search_query only
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
        "repos": {
            "search_query": '"set up working directory by installing dependencies" 0.92.2'
        }
    }
    
    config = create_config_from_task_definition(task_def)
    assert isinstance(config, RunAgentConfig)
    assert config.repos == mock_repos_from_query
    mock_get_repos.assert_called_with(None, '"set up working directory by installing dependencies" 0.92.2')
    
    # Test with both include and search_query - SHOULD COMBINE RESULTS
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
        "repos": {
            "include": [
                "chanzuckerberg/patchstorm",
                "chanzuckerberg/fogg"
            ],
            "search_query": '"set up working directory by installing dependencies" 0.92.2'
        }
    }
    
    config = create_config_from_task_definition(task_def)
    assert isinstance(config, RunAgentConfig)
    # Should combine both sets of repositories
    expected_repos = {"chanzuckerberg/patchstorm", "chanzuckerberg/fogg", "found/repo1", "found/repo2"}
    assert config.repos == expected_repos
    mock_get_repos.assert_called_with(None, '"set up working directory by installing dependencies" 0.92.2')
    
    # Command line override of repos
    config = create_config_from_task_definition(task_def, repos="override/repo")
    assert config.repos == {"override/repo"}
    mock_get_repos.assert_called_with("override/repo", None)


@mock.patch('run_agent.get_repos')
def test_convert_task_def_with_draft_to_config(mock_get_repos):
    """Test that draft defined in task definition is used in RunAgentConfig."""
    # Setup mock to return a set of repos
    mock_get_repos.return_value = {"test/repo"}
    
    # Test with draft=true in task definition - using new object format
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
        "repos": {
            "include": ["test/repo"]
        },
        "draft": True
    }
    
    config = create_config_from_task_definition(task_def_with_draft)
    assert isinstance(config, RunAgentConfig)
    assert config.draft is True
    
    # Test with draft=false in task definition - using new object format
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
        "repos": {
            "include": ["test/repo"]
        },
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


@mock.patch('run_agent.get_repos')
def test_task_def_with_both_legacy_repos_and_search_query(mock_get_repos):
    """Test that legacy repos format with search_query now fails with a ValueError."""
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
        # Legacy format is no longer supported
        "repos": ["mygithuborg/repo1", "mygithuborg/repo2"],
        "search_query": "path:.github language:YAML"
    }
    
    # Test should raise ValueError because legacy format is no longer supported
    with pytest.raises(ValueError) as excinfo:
        create_config_from_task_definition(task_def)
    
    assert "'repos' must be an object" in str(excinfo.value)
    
    
def test_task_def_with_conflicting_search_queries():
    """Test that specifying both repos.search_query and top-level search_query raises NotImplementedError."""
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
        "repos": {
            "search_query": "query1"
        },
        "search_query": "query2"
    }
    
    with pytest.raises(NotImplementedError) as excinfo:
        create_config_from_task_definition(task_def)
    assert "Cannot specify both 'repos.search_query' and top-level 'search_query'" in str(excinfo.value)


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