# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the lascheck package first (local package)
COPY lascheck ./lascheck

# Copy requirements and project files

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./lascheck && \
    pip install --no-cache-dir flask gunicorn

# Copy the rest of the application
COPY app.py ./
COPY Test_1.py Test_2.py Test_3.py ./
COPY static ./static
COPY templates ./templates

# Expose the port the app runs on
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Run the application with gunicorn for production
# Use 4 workers for better performance
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]