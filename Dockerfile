# ---------- BUILDER ----------
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt


# ---------- RUNTIME ----------
FROM python:3.11-slim

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY --from=builder /opt/venv /opt/venv

# Instala o Chromium no mesmo cache usado pelo usuario de runtime.
RUN playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

COPY config ./config
COPY core ./core
COPY webapp ./webapp

RUN mkdir -p /app/dist /app/webapp/uploads /app/webapp/exports && \
    cp -a /app/webapp/static/. /app/dist/

RUN useradd -m appuser && chown -R appuser:appuser /app /opt/venv /ms-playwright

USER appuser

EXPOSE 8000

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "webapp.server:app", "--host", "0.0.0.0", "--port", "8000"]
