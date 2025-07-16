import os


if os.environ.get('TEST_MODE', '').lower() in ('1', 'true'):
    GIT_NAME = 'test'
    GIT_EMAIL = 'test'
    GITHUB_PROJECT = 'test'
    GITHUB_TOKEN = 'test'
    GITHUB_ORGANIZATION = 'test'
    ARTIFACTS_DIR = '/tmp/artifacts'
else:
    GITHUB_ORGANIZATION = os.environ['GITHUB_ORGANIZATION']
    GIT_NAME = os.environ['GIT_NAME']
    GIT_EMAIL = os.environ['GIT_EMAIL']
    GITHUB_PROJECT = os.environ['GITHUB_PROJECT']
    with open(os.environ['GITHUB_TOKEN_FILE'], 'r') as f:
        GITHUB_TOKEN = f.read().strip()
    ARTIFACTS_DIR = '/app/artifacts'
