#!/bin/sh
set -euxo pipefail

docker build -t claude_code:latest /agent_images/claude_code
docker build -t codex:latest /agent_images/codex


# can move everything below to a new script in the MCP directory and run a new docker container to parallelize
  
if ! docker network inspect appnet >/dev/null 2>&1; then
  docker network create appnet
fi

# if you run make down, the containers will be in the stopped state when you run make up again
docker start ollama || true
docker start patchstorm_mcp || true
#run Ollama on the docker network as http://ollama:11434
if ! docker ps -a --format '{{.Names}}' | grep -w ollama >/dev/null 2>&1; then
  docker run -d \
    --name ollama \
    --network appnet \
    --network-alias ollama \
    -v ollama:/root/.ollama \
    -p 11434:11434 \
    ollama/ollama
fi

sleep 5  # give ollama a few seconds to start
docker exec ollama ollama pull llama3.2

docker build -t patchstorm_mcp:latest /mcp
if ! docker ps -a --format '{{.Names}}' | grep -w patchstorm_mcp >/dev/null 2>&1; then
  docker run -d \
    --name patchstorm_mcp \
    -e GITHUB_TOKEN="$(cat $GITHUB_TOKEN_FILE)" \
    -e OLLAMA_HOST="ollama:11434" \
    --network appnet \
    --network-alias patchstorm_mcp \
    -p 8000:8000 \
    patchstorm_mcp:latest
fi
