# --- Builder: resolve and install dependencies into site-packages ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# --- Runtime: copy only what's needed to run, drop root ---
FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --uid 1000 policyiq
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY main.py ./
COPY config ./config
COPY src ./src
COPY scripts ./scripts
COPY ui ./ui
COPY data ./data

RUN mkdir -p /app/logs /app/vectorstore \
    && chown -R policyiq:policyiq /app

USER policyiq
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

# Default: launch the dashboard. Ingest first, e.g.:
#   docker run --env-file .env -v policyiq_data:/app/vectorstore policyiq python scripts/ingest.py
CMD ["python", "ui/app.py"]
