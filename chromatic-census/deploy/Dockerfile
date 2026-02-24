FROM python:3.12-slim

WORKDIR /app

# System deps for numpy/scipy C extensions and OpenMP
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY config.yaml .
COPY run.py .
COPY data/ data/

# Create output directories
RUN mkdir -p /app/output/checkpoints /app/output/snapshots /app/output/final

ENV PYTHONUNBUFFERED=1

EXPOSE 8084

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8084/health')" || exit 1

# Default: fine grid with auto-resume (safe for container restarts)
CMD ["python", "run.py", "--mode", "fine", "--resume"]
