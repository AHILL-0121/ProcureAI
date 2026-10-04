# syntax=docker/dockerfile:1

# ---- deps: install Python packages into an isolated venv ----
FROM python:3.11-slim-bookworm AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- run: slim runtime with Tesseract, non-root ----
FROM python:3.11-slim-bookworm AS run
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH \
    APP_ENV=production APP_PORT=8001
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 procure

WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
# Copy only what the app needs at runtime, so .env / .env.local secrets never land in the image
COPY --chown=procure:procure alembic.ini ./
COPY --chown=procure:procure alembic ./alembic
COPY --chown=procure:procure data ./data
COPY --chown=procure:procure samples ./samples
COPY --chown=procure:procure app ./app
RUN mkdir -p /app/uploads && chown procure:procure /app/uploads
USER procure

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", os.environ[\"APP_PORT\"])}/api/ping', timeout=4)"

# DATABASE_URL (Neon) comes from the environment; the app migrates it on start. Render/Railway inject $PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-$APP_PORT} --proxy-headers --forwarded-allow-ips='*'"]
