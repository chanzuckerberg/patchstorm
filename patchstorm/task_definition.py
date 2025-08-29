from jsonschema import validate, ValidationError
import yaml

SCHEMA_YAML = """
type: object
required: [agent, commit, prompts]
properties:
  agent:
    type: object
    required: [provider]
    properties:
      provider:
        type: string
        description: The provider of the agent.
        enum:
          - codex
          - claude_code
  commit:
    type: object
    required: [message]
    properties:
      message:
        type: string
        description: The commit message to use.
  prompts:
    type: array
    items:
      type: object
      required: [prompt]
      properties:
        prompt:
          type: string
  repos:
    type: object
    description: Repository configuration for running tasks.
    properties:
      include:
        type: array
        description: List of repositories to run against.
        items:
          type: string
      search_query:
        type: string
        description: GitHub search query to find repositories.
  search_query:
    type: string
    description: GitHub search query to find repositories (legacy format, prefer repos.search_query).
  draft:
    type: boolean
    description: Whether to create pull requests as drafts. Defaults to false if not specified.
"""

SCHEMA = yaml.safe_load(SCHEMA_YAML)

def validate_task_definition_yaml(yml_str):
    """
    Validate the task definition YAML string against the schema.
    """
    try:
        yaml_obj = yaml.safe_load(yml_str)
        print(yaml_obj)
        validate(yaml_obj, SCHEMA)
        return True
    except ValidationError as e:
        raise ValueError(f"YAML validation error: {e.message}")