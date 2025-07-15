#!/bin/sh
set -euxo pipefail

docker build -t claude_code:latest /agent_images/claude_code
docker build -t codex:latest /agent_images/codex
