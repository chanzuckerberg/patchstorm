FROM python:3.11-slim

WORKDIR /app

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system

# Copy all necessary files
COPY mcp_server.py .

# Expose the HTTP port
EXPOSE 8000

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8000

# Run the server with uvicorn
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8000"]
