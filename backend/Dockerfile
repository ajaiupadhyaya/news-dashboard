# News & Markets Dashboard — backend container (Fly.io).
# Build context is the backend/ directory.
FROM python:3.12-slim

# No .pyc files; unbuffered stdout so logs stream straight to Fly.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first — this layer is cached across code-only changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application package.
COPY app ./app

# Fly routes public HTTPS traffic to this internal port.
EXPOSE 8080

# Single worker: APScheduler runs in-process and must not be duplicated.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
