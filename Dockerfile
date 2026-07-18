# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install production dependencies first (cached until pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-warn-script-location "setuptools>=68.0" && \
    pip install --no-cache-dir --no-warn-script-location ".[dev]"


# ---- Runtime stage ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY app/ ./app/
COPY pyproject.toml ./

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
