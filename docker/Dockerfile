# syntax=docker/dockerfile:1.7
# See README.md for build/run instructions and Claude Desktop config.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.14-slim-bookworm AS runtime

RUN groupadd --system mcp && useradd --system --gid mcp --create-home mcp

WORKDIR /app
COPY --from=builder --chown=mcp:mcp /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SALDEO_LOG_DIR=/var/log/saldeosmart

RUN mkdir -p /var/log/saldeosmart && chown mcp:mcp /var/log/saldeosmart

VOLUME ["/var/log/saldeosmart"]

USER mcp

ENTRYPOINT ["saldeosmart-mcp"]
