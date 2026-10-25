FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY src ./src

CMD ["uv", "run", "--no-sync", "python", "-m", "src.entrypoints.worker"]
