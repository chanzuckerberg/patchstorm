import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from patchstorm.run_agent_config import RunAgentConfig
from tasks.github_tasks import clone_and_run_prompt


class TestCloneAndRunPrompt(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        
        # Create test config
        self.test_config = RunAgentConfig(
            commit_msg="Test commit message",
            prompts=["Test prompt"],
            agent_provider="codex",
            repos={"test/repo"},
            skip_pr=True,
            dry=False
        )
        
        # Set environment variables needed for the test
        os.environ['GIT_NAME'] = 'Test User'
        os.environ['GIT_EMAIL'] = 'test@example.com'
        os.environ['GITHUB_TOKEN_FILE'] = os.path.join(self.test_dir, 'token_file')
        
        # Create a token file
        with open(os.environ['GITHUB_TOKEN_FILE'], 'w') as f:
            f.write('test_token')
    
    def tearDown(self):
        # Clean up the temp directory
        shutil.rmtree(self.test_dir)
        
    @patch('tasks.github_tasks._clone_repo')
    @patch('tasks.github_tasks._run_agent')
    def test_clone_and_run_prompt(self, mock_run_agent, mock_clone_repo):
        # Configure the mocks
        repo_name = "test/repo"
        run_id = "test_run_id"
        repo_dir = f"/app/artifacts/{repo_name}_{run_id}"
        
        # Instead of cloning a real repo let's create a new directory, run git init, put in a fake README, and commit
        def mock_clone_implementation(repo_name, repo_dir):
            # Create repo dir
            os.makedirs(repo_dir, exist_ok=True)
            
            with open(os.path.join(repo_dir, "README.md"), "w") as f:
                f.write("# Test Repository\n\nThis is a test repository.")
            
            os.system(f"cd {repo_dir} && git init && git checkout -b main && git add README.md && git -c user.name='Test' -c user.email='test@example.com' commit -m 'Initial commit'")
        
        mock_clone_repo.side_effect = mock_clone_implementation
        
        # Instead of running a real agent we're going to add a fake change
        def mock_run_agent_implementation(config, repo_dir, run_id):
            # Add a line to README.md
            with open(os.path.join(repo_dir, "README.md"), "a") as f:
                f.write("\n\nThis line was added by the AI agent.")
            
            # Return mock output including JSON stats
            return "Mock agent output\n{\"cost_usd\": 0.01, \"duration_ms\": 1000, \"duration_api_ms\": 500, \"role\": \"test\"}"
        
        mock_run_agent.side_effect = mock_run_agent_implementation

        # Run the function with patches
        with patch('uuid.uuid4', return_value=MagicMock(hex=run_id)):
            clone_and_run_prompt(repo_name, self.test_config)
        
        # Verify the mocks were called correctly
        mock_clone_repo.assert_called_once_with(repo_name, repo_dir)
        mock_run_agent.assert_called_once_with(self.test_config, repo_dir, run_id)

        # Check if the README.md was modified
        with open(os.path.join(repo_dir, "README.md"), "r") as f:
            content = f.read()
            self.assertIn("This line was added by the AI agent.", content)
