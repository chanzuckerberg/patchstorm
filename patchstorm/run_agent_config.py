from dataclasses import dataclass, asdict
from typing import Set, Dict, Any, List, ClassVar, Type
import json


@dataclass
class RunAgentConfig:
    """Configuration for running an agent."""
    commit_msg: str
    prompts: list[str]  # List of prompts to be processed
    agent_provider: str
    repos: Set[str]
    skip_pr: bool = False
    dry: bool = False
    reviewers: Set[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the config to a dictionary."""
        config_dict = asdict(self)
        
        # Convert sets to lists for JSON serialization
        config_dict['repos'] = list(config_dict['repos'])
        
        # Handle reviewers set if it exists
        if config_dict['reviewers'] is not None:
            config_dict['reviewers'] = list(config_dict['reviewers'])
        
        return config_dict
    
    def to_json(self) -> str:
        """Convert the config to a JSON string."""
        return json.dumps(self.to_dict())
        
    def __iter__(self):
        """Make the dataclass iterable for dict() conversion."""
        yield from self.to_dict().items()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RunAgentConfig':
        """Create a RunAgentConfig instance from a JSON string.
        
        Args:
            json_str: JSON string representation of RunAgentConfig
            
        Returns:
            RunAgentConfig instance
        """
        data = json.loads(json_str)
        # Convert repos back to a set if it's a list or another iterable
        if 'repos' in data and not isinstance(data['repos'], set):
            data['repos'] = set(data['repos'])
            
        # Convert reviewers back to a set if it's a list or another iterable
        if 'reviewers' in data and data['reviewers'] is not None and not isinstance(data['reviewers'], set):
            data['reviewers'] = set(data['reviewers'])
            
        return cls(**data)
