# Multi-stage production Dockerfile for ZipPrompt API
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Run as non-root user for security
RUN groupadd -r zipprompt && useradd -r -g zipprompt zipprompt

COPY --from=builder /root/.local /home/zipprompt/.local
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY data/ /app/data/

ENV PATH=/home/zipprompt/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

USER zipprompt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
