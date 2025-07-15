import json
import unittest
from patchstorm.run_agent_config import RunAgentConfig


class TestRunAgentConfig(unittest.TestCase):
    def test_serialization(self):
        original_config = RunAgentConfig(
            commit_msg="Original message",
            prompts=["Original prompt", "Some other prompt"],
            agent_provider="claude_code",
            repos={"original_repo"},
            skip_pr=True,
            dry=False
        )
        
        # Convert to JSON and back to a new config
        json_str = original_config.to_json()
        new_config = RunAgentConfig.from_json(json_str)
        
        # Verify the new config matches the original
        self.assertEqual(new_config.commit_msg, original_config.commit_msg)
        self.assertEqual(new_config.prompts, original_config.prompts)
        self.assertEqual(new_config.agent_provider, original_config.agent_provider)
        self.assertEqual(new_config.repos, original_config.repos)
        self.assertEqual(new_config.skip_pr, original_config.skip_pr)
        self.assertEqual(new_config.dry, original_config.dry)
        self.assertEqual(new_config.reviewers, original_config.reviewers)
        
    def test_serialization_with_reviewers(self):
        original_config = RunAgentConfig(
            commit_msg="Test message",
            prompts=["Test prompt"],
            agent_provider="codex",
            repos={"test_repo"},
            skip_pr=False,
            dry=True,
            reviewers={"user1", "user2"}
        )
        
        # Convert to JSON and back to a new config
        json_str = original_config.to_json()
        new_config = RunAgentConfig.from_json(json_str)
        
        # Verify the new config matches the original
        self.assertEqual(new_config.commit_msg, original_config.commit_msg)
        self.assertEqual(new_config.prompts, original_config.prompts)
        self.assertEqual(new_config.agent_provider, original_config.agent_provider)
        self.assertEqual(new_config.repos, original_config.repos)
        self.assertEqual(new_config.skip_pr, original_config.skip_pr)
        self.assertEqual(new_config.dry, original_config.dry)
        self.assertEqual(new_config.reviewers, original_config.reviewers)
        
    def test_to_dict_serializes_reviewers(self):
        config = RunAgentConfig(
            commit_msg="Test message",
            prompts=["Test prompt"],
            agent_provider="codex",
            repos={"test_repo"},
            reviewers={"user1", "user2"}
        )
        
        config_dict = config.to_dict()
        
        # Verify that both repos and reviewers are properly serialized
        self.assertIn("repos", config_dict)
        self.assertIsInstance(config_dict["repos"], list)
        
        self.assertIn("reviewers", config_dict)
        self.assertIsInstance(config_dict["reviewers"], list)
