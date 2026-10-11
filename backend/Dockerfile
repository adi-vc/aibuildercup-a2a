# Dockerfile — Vachan API (FastAPI on Cloud Run)
#
# Build:  docker build -t vachan-api ./backend
# Run:    docker run -p 8080:8080 --env-file backend/.env vachan-api
#
# Cloud Run deploys this image automatically via cloudbuild.yaml.
# The container must listen on $PORT (Cloud Run injects 8080 by default).

# ── Stage 1: deps ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /build

# Install system packages needed to build cryptography + grpcio wheels.
# slim image omits gcc; we install then prune in the final stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for Cloud Run security best-practice
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser manifest_schema/ ./manifest_schema/
COPY --chown=appuser:appuser fixtures/ ./fixtures/

# Cloud Run injects PORT; default to 8080 for local docker run
ENV PORT=8080

# Gunicorn in prod; uvicorn --reload is handled by docker-compose for local dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"
