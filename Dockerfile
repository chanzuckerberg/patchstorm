FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    git \
    gh \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install docker cli
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
RUN chmod a+r /etc/apt/keyrings/docker.asc
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "bookworm") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update
RUN apt-get install -y --no-install-recommends docker-ce-cli

ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Add a non-root user to run the worker
RUN useradd -ms /bin/bash celeryuser
COPY --chown=celeryuser:celeryuser . .



CMD ["celery", "-A", "tasks.celery", "worker", "--loglevel=info", "--uid=celeryuser"]
