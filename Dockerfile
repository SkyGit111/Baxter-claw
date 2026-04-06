FROM python:3.10-slim

LABEL maintainer="your-email@example.com"
LABEL description="Baxter-Claw Bridge Server"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY bridge/ ./bridge/
COPY config/ ./config/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose bridge server port
EXPOSE 8420

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8420/health || exit 1

# Default command
CMD ["baxter-claw-bridge", "--config", "config/baxter.example.yaml", "--host", "0.0.0.0"]
