#!/bin/bash
set -euxo pipefail
if [ -z "$1" ]; then
    echo "Usage: $0 <file_name>"
    exit 1
fi

cat $1 | docker compose exec -T worker python run_agent.py "${@:2}"