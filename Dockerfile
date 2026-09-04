FROM ghcr.io/astral-sh/uv:0.12.9 AS uv
FROM python:3.12.14-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

FROM python:3.12.14-slim
RUN groupadd --system keyport && useradd --system --gid keyport --home /app keyport && mkdir -p /data && chown keyport:keyport /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=keyport:keyport . .
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER keyport
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=* --no-access-log"]
