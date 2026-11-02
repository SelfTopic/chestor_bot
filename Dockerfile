
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_PATH=/opt/poetry-venvs

RUN rm -f /etc/apt/apt.conf.d/docker-clean

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install poetry

WORKDIR /app


FROM base AS builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-root --no-ansi


FROM base AS runtime

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg

COPY --from=builder /opt/poetry-venvs /opt/poetry-venvs

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/media-tools \
    && /opt/media-tools/bin/pip install "yt-dlp[default,curl-cffi]" gallery-dl

COPY . .

CMD ["poetry", "run", "python", "-m", "src.bot"]
