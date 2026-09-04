# NIYAM Multi-Stage Production Container
FROM python:3.12-slim AS builder

WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create non-root runtime user for security
RUN useradd -m -u 1001 niyamuser && \
    mkdir -p data && \
    chown -R niyamuser:niyamuser /app

USER niyamuser

# Expose default port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/healthz || exit 1

# Launch Gateway with dynamic $PORT support
CMD ["sh", "-c", "uvicorn services.gateway.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
