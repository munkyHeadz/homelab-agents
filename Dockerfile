FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-docker.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY crews/ ./crews/
COPY agent_server.py .
COPY .env .

# Expose Flask port
EXPOSE 5000

# Run the agent server
CMD ["python", "agent_server.py"]
