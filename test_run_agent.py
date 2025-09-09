import os
import sys
import unittest
import unittest.mock as mock
from argparse import Namespace
import io
import pytest
from typing import Set

# Import the module to test
import run_agent
from patchstorm.run_agent_config import RunAgentConfig
from patchstorm.exceptions import PatchStormParserError


class TestRunAgent(unittest.TestCase):
    """Test the run_agent.py main function with various inputs."""

    def setUp(self):
        # Create a patch for the get_repos function that returns a controlled set of repos
        self.get_repos_patcher = mock.patch('run_agent.get_repos')
        self.mock_get_repos = self.get_repos_patcher.start()
        
        # Create a patch for the get_repo_prs function
        self.get_repo_prs_patcher = mock.patch('run_agent.get_repo_prs')
        self.mock_get_repo_prs = self.get_repo_prs_patcher.start()
        self.mock_get_repo_prs.return_value = []
        
        # Create a patch for clone_and_run_prompt.delay
        self.clone_patcher = mock.patch('run_agent.clone_and_run_prompt.delay')
        self.mock_clone_delay = self.clone_patcher.start()
    
    def tearDown(self):
        self.get_repos_patcher.stop()
        self.get_repo_prs_patcher.stop()
        self.clone_patcher.stop()

    def test_main_with_task_definition(self):
        """Test main with a task definition file."""
        # Setup mocks
        self.mock_get_repos.return_value = {"test/repo1", "test/repo2"}
        
        # Create a mock args object
        args = Namespace(
            task_definition="test_task_definition.yaml",
            prompt=None,
            repos=None,
            search_query=None,
            dry=False,
            skip_pr=False,
            reviewers=None,
            draft=None,
            agent_provider=None,
            commit_msg=None
        )
        
        # Mock the load_task_definition function
        with mock.patch('run_agent.load_task_definition') as mock_load_task_def:
            # Define a task definition similar to what would be loaded from YAML
            mock_task_def = {
                "agent": {
                    "provider": "claude_code"
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
                    "include": ["test/repo1", "test/repo2"]
                }
            }
            mock_load_task_def.return_value = mock_task_def
            
            # Call the function under test
            run_agent.main(args)
            
            # Assertions
            mock_load_task_def.assert_called_with("test_task_definition.yaml")
            self.mock_get_repo_prs.assert_any_call("test/repo1")
            self.mock_get_repo_prs.assert_any_call("test/repo2")
            
            # Check that clone_and_run_prompt was called for both repos
            self.assertEqual(self.mock_clone_delay.call_count, 2)
            
            # Check that the calls were with the right repos
            repos_in_calls = {call[0][0] for call in self.mock_clone_delay.call_args_list}
            self.assertEqual(repos_in_calls, {"test/repo1", "test/repo2"})

    def test_main_with_prompt(self):
        """Test main with a direct prompt."""
        # Setup mocks
        self.mock_get_repos.return_value = {"test/repo1"}
        
        # Create a mock args object with a prompt and commit message
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="test/repo1",
            search_query=None,
            dry=False,
            skip_pr=False,
            reviewers=None,
            draft=False,
            agent_provider="codex",
            commit_msg="Test commit message"
        )
        
        # Call the function under test
        run_agent.main(args)
        
        # Assertions
        self.mock_get_repos.assert_called_with("test/repo1", None)
        self.mock_get_repo_prs.assert_called_with("test/repo1")
        
        # Check that clone_and_run_prompt was called once
        self.mock_clone_delay.assert_called_once()
        call_args = self.mock_clone_delay.call_args[0]
        self.assertEqual(call_args[0], "test/repo1")
        
        # Check that the config JSON passed to clone_and_run_prompt is correct
        config = RunAgentConfig.from_json(call_args[1])
        self.assertEqual(config.prompts, ["Test prompt"])
        self.assertEqual(config.commit_msg, "Test commit message")
        self.assertEqual(config.agent_provider, "codex")
        self.assertEqual(config.repos, {"test/repo1"})
        self.assertFalse(config.skip_pr)
        self.assertFalse(config.dry)
        self.assertFalse(config.draft)

    def test_main_with_search_query(self):
        """Test main with a search query."""
        # Setup mocks
        self.mock_get_repos.return_value = {"found/repo1", "found/repo2"}
        
        # Create a mock args object with a search query
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos=None,
            search_query="language:python path:.github",
            dry=False,
            skip_pr=False,
            reviewers="user1,user2",
            draft=True,
            agent_provider="codex",
            commit_msg="Test commit message"
        )
        
        # Call the function under test
        run_agent.main(args)
        
        # Assertions
        self.mock_get_repos.assert_called_with(None, "language:python path:.github")
        
        # Check that clone_and_run_prompt was called twice (once for each repo)
        self.assertEqual(self.mock_clone_delay.call_count, 2)
        
        # Verify one of the calls
        for call in self.mock_clone_delay.call_args_list:
            repo = call[0][0]
            self.assertIn(repo, {"found/repo1", "found/repo2"})
            config = RunAgentConfig.from_json(call[0][1])
            self.assertEqual(config.reviewers, {"user1", "user2"})
            self.assertTrue(config.draft)

    def test_main_with_stdin_task_definition(self):
        """Test main with task definition from stdin."""
        # Setup mocks
        self.mock_get_repos.return_value = {"test/repo1"}
        
        # Mock stdin to return a task definition
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = False
            mock_stdin.read.return_value = """
            agent:
              provider: claude_code
            commit:
              message: Test stdin commit message
            prompts:
              - prompt: Test stdin prompt
            repos:
              include:
                - test/repo1
            """
            
            # Create a mock args object without task_definition or prompt
            args = Namespace(
                task_definition=None,
                prompt=None,
                repos=None,
                search_query=None,
                dry=False,
                skip_pr=False,
                reviewers=None,
                draft=None,
                agent_provider=None,
                commit_msg=None
            )
            
            # Mock the validate_task_definition_yaml function
            with mock.patch('run_agent.validate_task_definition_yaml') as mock_validate:
                mock_validate.return_value = True
                
                # Call the function under test
                run_agent.main(args)
            
            # Assertions
            mock_stdin.read.assert_called_once()
            self.mock_get_repo_prs.assert_called_with("test/repo1")
            self.mock_clone_delay.assert_called_once()
            
            # Verify the config
            call_args = self.mock_clone_delay.call_args[0]
            self.assertEqual(call_args[0], "test/repo1")
            config = RunAgentConfig.from_json(call_args[1])
            self.assertEqual(config.commit_msg, "Test stdin commit message")
            self.assertEqual(config.prompts, ["Test stdin prompt"])
            self.assertEqual(config.agent_provider, "claude_code")

    def test_main_dry_run(self):
        """Test dry run mode."""
        # Setup mocks
        self.mock_get_repos.return_value = {"test/repo"}
        
        # Create a mock args object with dry=True
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="test/repo",
            search_query=None,
            dry=True,
            skip_pr=False,
            reviewers=None,
            draft=None,
            agent_provider="codex",
            commit_msg="Test commit message"
        )
        
        # Capture stdout to check dry run output
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # Call the function under test
            run_agent.main(args)
            
            # Assertions
            output = captured_output.getvalue()
            self.assertIn("would run with prompts: ['Test prompt']", output)
            self.assertIn("commit message: Test commit message", output)
            self.assertIn("agent provider: codex", output)
            self.assertIn("Would run on test/repo", output)
            
            # Make sure the task was not actually submitted
            self.mock_clone_delay.assert_not_called()
        finally:
            sys.stdout = sys.__stdout__  # Reset stdout

    def test_main_no_inputs(self):
        """Test with no inputs provided."""
        # Create a mock args object with no inputs
        args = Namespace(
            task_definition=None,
            prompt=None,
            repos=None,
            search_query=None,
            dry=False,
            skip_pr=False,
            reviewers=None,
            draft=None,
            agent_provider=None,
            commit_msg=None
        )
        
        # Mock stdin to simulate empty stdin
        with mock.patch('sys.stdin') as mock_stdin:
            mock_stdin.isatty.return_value = True
            mock_stdin.read.return_value = None
            
            # We expect this to raise a PatchStormParserError due to no input
            with self.assertRaises(PatchStormParserError) as context:
                # Call the function under test
                run_agent.main(args)
            
            # Verify the error message
            self.assertEqual("You must provide a task definition file or a prompt.", context.exception.message)

    def test_main_missing_commit_message(self):
        """Test error when missing commit message."""
        # Create a mock args object missing commit message
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="test/repo",
            search_query=None,
            dry=False,
            skip_pr=False,  # Not skipping PR but missing commit message
            reviewers=None,
            draft=None,
            agent_provider="codex",
            commit_msg=None  # Missing commit message
        )
        
        # Mock get_repos to avoid GitHub API calls
        with mock.patch('run_agent.get_repos') as mock_get_repos:
            mock_get_repos.return_value = {"test/repo"}
            
            # We expect this to raise a PatchStormParserError due to missing commit message
            with self.assertRaises(PatchStormParserError) as context:
                # Call the function under test
                run_agent.main(args)
            
            # Verify the error message
            self.assertEqual("You must provide a commit message with --commit-msg", context.exception.message)
    
    def test_create_config_from_args_missing_commit_message(self):
        """Test that create_config_from_args raises an error when commit message is missing."""
        # Create a mock args object missing commit message
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="test/repo",
            search_query=None,
            dry=False,
            skip_pr=False,  # Not skipping PR but missing commit message
            reviewers=None,
            draft=None,
            agent_provider="codex",
            commit_msg=None  # Missing commit message
        )
        
        # Mock get_repos to avoid GitHub API calls
        with mock.patch('run_agent.get_repos') as mock_get_repos:
            mock_get_repos.return_value = {"test/repo"}
            
            # We expect this to raise a PatchStormParserError due to missing commit message
            with self.assertRaises(PatchStormParserError) as context:
                # Call the function under test directly
                run_agent.create_config_from_args(args)
            
            # Verify the error message
            self.assertEqual("You must provide a commit message with --commit-msg", context.exception.message)

    def test_skip_repos_with_existing_prs(self):
        """Test that repos with existing PRs are skipped."""
        # Setup mocks
        self.mock_get_repos.return_value = {"repo/with_pr", "repo/without_pr"}
        
        # Mock to simulate one repo already has a PR with same title
        def get_repo_prs_side_effect(repo):
            if repo == "repo/with_pr":
                # Create a mock PR object with a title matching the commit message
                mock_pr = mock.MagicMock()
                mock_pr.title = "Test commit message"
                return [mock_pr]
            else:
                return []
                
        self.mock_get_repo_prs.side_effect = get_repo_prs_side_effect
        
        # Create a mock args object
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="repo/with_pr,repo/without_pr",
            search_query=None,
            dry=False,
            skip_pr=False,
            reviewers=None,
            draft=None,
            agent_provider="codex",
            commit_msg="Test commit message"
        )
        
        # Call the function under test
        run_agent.main(args)
        
        # Assertions
        self.mock_get_repos.assert_called_with("repo/with_pr,repo/without_pr", None)
        
        # Check that clone_and_run_prompt was called only for repo/without_pr
        self.mock_clone_delay.assert_called_once()
        call_args = self.mock_clone_delay.call_args[0]
        self.assertEqual(call_args[0], "repo/without_pr")

    def test_main_with_reviewers(self):
        """Test main with reviewers."""
        # Setup mocks
        self.mock_get_repos.return_value = {"test/repo"}
        
        # Create a mock args object with reviewers
        args = Namespace(
            task_definition=None,
            prompt="Test prompt",
            repos="test/repo",
            search_query=None,
            dry=False,
            skip_pr=False,
            reviewers="user1,user2,user3",
            draft=False,
            agent_provider="codex",
            commit_msg="Test commit message"
        )
        
        # Call the function under test
        run_agent.main(args)
        
        # Assertions
        self.mock_get_repos.assert_called_with("test/repo", None)
        self.mock_get_repo_prs.assert_called_with("test/repo")
        
        # Check that the reviewers were set correctly
        self.mock_clone_delay.assert_called_once()
        call_args = self.mock_clone_delay.call_args[0]
        config = RunAgentConfig.from_json(call_args[1])
        self.assertEqual(config.reviewers, {"user1", "user2", "user3"})


if __name__ == "__main__":
    pytest.main()