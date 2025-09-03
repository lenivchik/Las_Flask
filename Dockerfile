# Use Python 3.11 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set work directory
WORKDIR /app

# Install system dependencies including Poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        build-essential \
    && pip install --no-cache-dir poetry==1.7.1 \
    && rm -rf /var/lib/apt/lists/*

# Configure Poetry to not create virtual environments (using correct key)
RUN poetry config virtualenvs.create false

# Copy Poetry files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Copy local lascheck package (including its own pyproject.toml)
COPY lascheck/ ./lascheck/

# Install lascheck dependencies first (if it has its own pyproject.toml)
RUN if [ -f "./lascheck/pyproject.toml" ]; then \
        echo "Installing lascheck dependencies..." && \
        cd ./lascheck && \
        poetry install --only=main && \
        cd .. ; \
    else \
        echo "No pyproject.toml found in lascheck, skipping..." ; \
    fi

# Install main app dependencies with Poetry
RUN poetry install --only=main \
    && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]