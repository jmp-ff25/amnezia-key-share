FROM ghcr.io/astral-sh/uv:0.12.9 AS uv
FROM python:3.12.14-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/* \
    && groupadd --system keyport && useradd --system --gid keyport --home /app keyport && mkdir -p /data && chown keyport:keyport /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=keyport:keyport . .
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
