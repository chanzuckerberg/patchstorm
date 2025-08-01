.PHONY: up down restart rebuild clean logs test run-github-demo test-new-tasks artifacts help

# Default target
help:
	@echo "Available targets:"
	@echo "  make up             - Start the Docker Compose stack"
	@echo "  make down           - Stop the Docker Compose stack"
	@echo "  make restart        - Restart the worker service"
	@echo "  make rebuild        - Rebuild and restart the Docker Compose stack"
	@echo "  make clean          - Stop and remove containers, networks, and volumes"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-worker    - View logs from the worker service"

# Start the Docker Compose stack
up: .env.github
	@if [ -f ./custom_setup.sh ]; then bash custom_setup.sh; fi
	mkdir -p artifacts
	touch .env.aws
	@gh auth status
	@echo "Starting Docker Compose stack..."
	@GITHUB_TOKEN=$(shell gh auth token) docker-compose up -d
	@echo "Services are running in the background."
	@echo "Use 'make logs' to view logs."

# Stop the Docker Compose stack
down: .env.github
	@echo "Stopping Docker Compose stack..."
	docker-compose down
	@echo "Services stopped."

# Restart the worker
restart: .env.github
	@echo "Restarting worker..."
	@if [ -f ./myscript.sh ]; then bash custom_setup.sh; fi
	docker-compose restart worker
	@echo "Services restarted."

# Rebuild and restart the Docker Compose stack
rebuild: .env.github
	@echo "Rebuilding Docker Compose stack..."
	docker-compose build
	$(MAKE) up
	@echo "Services rebuilt and restarted."

# Stop and remove containers, networks, and volumes
clean:
	@echo "Cleaning up Docker Compose resources..."
	docker-compose down --volumes --remove-orphans
	rm .env.github
	@echo "Cleanup complete."

sh:
	docker-compose exec worker /bin/bash

# View logs from all services
logs:
	docker-compose logs -f

# View logs from the worker service
logs-worker:
	docker-compose logs -f worker

test:
	GITHUB_TOKEN=test docker compose run -e TEST_MODE=true worker pytest --ignore=artifacts --verbose

openflower:
	open http://localhost:5555

.env.github:
	echo GIT_EMAIL=$(shell git config get user.email) > .env.github
	echo GIT_NAME=\"$(shell git config get user.name)\" >> .env.github
