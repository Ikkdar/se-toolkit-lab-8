# Stage 1: Builder
FROM harbor.pg.innopolis.university/docker-hub-cache/astral/uv:python3.14-bookworm-slim AS builder

WORKDIR /workspace

# Copy entire workspace from project root
COPY --from=workspace . /workspace

# Sync dependencies (this installs nanobot but not other workspace packages with --no-install-workspace)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Stage 2: Runtime
FROM harbor.pg.innopolis.university/docker-hub-cache/python:3.14.2-slim-bookworm AS runtime

# Create nonroot user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy from builder
COPY --from=builder --chown=nonroot:nonroot /workspace /workspace

WORKDIR /workspace/nanobot

USER nonroot

CMD ["python", "/workspace/nanobot/entrypoint.py"]
