FROM python:3.11.7-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV MISE_PYTHON_GITHUB_ATTESTATIONS=false
ENV PYTHON_GITHUB_ATTESTATIONS=false

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Run the bot
CMD ["python", "testbot (3).py"]
