#!/bin/sh
# check_patchstorm_status.sh
# 
# Script to verify that patchstorm is fully operational
# This script will be executed via docker-compose exec as part of 'make up'
#
# It verifies:
# 1. claude_code:latest image exists
# 2. codex:latest image exists  
# 3. ollama and patchstorm_mcp containers are running
# 4. ollama llama3.2 is operational via test query

set -e  # Exit immediately if a command exits with a non-zero status

echo "Checking Patchstorm operational status..."
echo "----------------------------------------"

# Color codes for output formatting
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check status and display result
check_status() {
  if [ $1 -eq 0 ]; then
    echo -e "${GREEN}[✓] $2${NC}"
    return 0
  else
    echo -e "${RED}[✗] $3${NC}"
    return 1
  fi
}

# Function to retry a command with a timeout
retry_with_timeout() {
  local cmd="$1"      # Command to execute
  local success_msg="$2"  # Success message
  local error_msg="$3"    # Error message
  local timeout=300    # 5 minutes timeout (in seconds)
  local interval=10    # Check every 10 seconds
  local start_time=$(date +%s)
  local end_time=$((start_time + timeout))
  local attempt=1
  
  echo "Attempting: $success_msg"
  
  while [ $(date +%s) -lt $end_time ]; do
    echo -n "Attempt $attempt: "
    
    # Execute the command
    eval "$cmd" > /dev/null 2>&1
    local result=$?
    
    if [ $result -eq 0 ]; then
      # Success
      echo -e "${GREEN}Success!${NC}"
      echo -e "${GREEN}[✓] $success_msg${NC}"
      return 0
    else
      # Failed attempt, will retry
      echo -e "${YELLOW}Failed, retrying in $interval seconds...${NC}"
      sleep $interval
      attempt=$((attempt + 1))
    fi
  done
  
  # If we got here, we've exceeded the timeout
  local duration=$(($(date +%s) - start_time))
  echo -e "${RED}[✗] $error_msg (Timed out after $duration seconds)${NC}"
  return 1
}

# Check if claude_code:latest image exists
check_claude_code_image() {
  echo "Checking if claude_code:latest image exists..."
  retry_with_timeout "docker image inspect claude_code:latest" \
                    "claude_code:latest image found" \
                    "claude_code:latest image not found after retrying for 5 minutes. Run 'make rebuild' to build the image"
}

# Check if codex:latest image exists
check_codex_image() {
  echo "Checking if codex:latest image exists..."
  retry_with_timeout "docker image inspect codex:latest" \
                    "codex:latest image found" \
                    "codex:latest image not found after retrying for 5 minutes. Run 'make rebuild' to build the image"
}

# Check if containers are running
check_container_status() {
  local success=0
  
  echo "Checking if ollama container is running..."
  retry_with_timeout "docker ps --format '{{.Names}}' | grep -w ollama" \
                    "ollama container is running" \
                    "ollama container is not running after retrying for 5 minutes. Check logs with 'docker logs ollama'" \
                    || success=1
  
  echo "Checking if patchstorm_mcp container is running..."
  retry_with_timeout "docker ps --format '{{.Names}}' | grep -w patchstorm_mcp" \
                    "patchstorm_mcp container is running" \
                    "patchstorm_mcp container is not running after retrying for 5 minutes. Check logs with 'docker logs patchstorm_mcp'" \
                    || success=1
  
  # Return overall container status
  return $success
}

# Test ollama with a simple query to ensure llama3.2 is working
test_ollama_query() {
  echo "Testing ollama llama3.2 with a simple query..."
  
  # Command to test ollama with retry
  retry_with_timeout "docker exec ollama ollama run llama3.2 'Respond with OK if you can process this message' 2>/dev/null | grep -i 'OK'" \
                    "ollama llama3.2 is operational" \
                    "ollama llama3.2 is not responding correctly after retrying for 5 minutes. Check the ollama container status"
}

# Run all checks
main() {
  echo "Running patchstorm operational status checks..."
  local errors=0
  
  # Check images
  check_claude_code_image || errors=$((errors + 1))
  check_codex_image || errors=$((errors + 1))
  
  # Check containers 
  check_container_status || errors=$((errors + 1))
  
  # Test ollama
  test_ollama_query || errors=$((errors + 1))
  
  echo "----------------------------------------"
  if [ $errors -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Patchstorm is fully operational.${NC}"
    exit 0
  else
    echo -e "${RED}Failed checks: $errors. Patchstorm is not fully operational.${NC}"
    echo -e "${YELLOW}Please check the error messages above and/or run docker-compose logs build_agent_imgs to resolve the issues.${NC}"
    exit 1
  fi
}

# Execute main function
main