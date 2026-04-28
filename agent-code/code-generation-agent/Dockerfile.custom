FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install build dependencies for packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Set the entrypoint
CMD ["python", "agents.py"]
