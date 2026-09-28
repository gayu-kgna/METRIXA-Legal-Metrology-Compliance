# ==============================================================================
# METRIXA Backend Container - Production Dockerfile
# Base: Python 3.11 Slim (Debian Bookworm)
# Includes: Tesseract OCR + OSD, OpenCV runtime libraries, Uvicorn ASGI Server
# ==============================================================================

FROM python:3.11-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    STORAGE_ROOT=/app/storage

# Install system dependencies:
# 1. Tesseract OCR with English trained models
# 2. OpenCV headless system libraries (libglib2.0-0, libsm6, libxext6, libxrender1)
# 3. System utilities (curl, ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract installation in container
RUN tesseract --version

WORKDIR /app

# Install Python dependencies first for caching efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend application source and database migration configurations
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create persistent storage mount directory for inspections and PDF reports
RUN mkdir -p /app/storage/inspections

# Expose port (defaults to 8080; Railway injects custom PORT at runtime)
EXPOSE 8080

# Health check against top-level health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Start Uvicorn binding to 0.0.0.0 and dynamically respecting the host PORT variable
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
