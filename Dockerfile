# Minimal working Dockerfile for your specific setup
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install lascheck (has setup.py, so pip will work)
COPY lascheck/ ./lascheck/
RUN pip install -e ./lascheck/

# Install Flask app dependencies
RUN pip install \
    flask==3.1.2 \
    gunicorn==21.2.0 \
    werkzeug==3.1.3 \
    jinja2==3.1.6 \
    markupsafe==3.0.2 \
    click==8.2.1 \
    blinker==1.9.0 \
    itsdangerous==2.2.0

# Copy Flask app
COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY Test_1.py ./
COPY Test_2.py ./

# Create directories and user
RUN mkdir -p uploads && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]