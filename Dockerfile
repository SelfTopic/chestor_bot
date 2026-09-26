# syntax=docker/dockerfile:1
# Два этапа: компиляторы и заголовки нужны только для сборки зависимостей
# (psycopg2, psycopg-c из исходников), в итоговый образ попадают готовое окружение,
# ffmpeg и libpq. Кэши apt/pip/poetry — BuildKit cache mounts: в слои не попадают,
# а при изменении poetry.lock пакеты не скачиваются заново.

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    # Окружение вне /app: bot/selfrot_bot монтируют туда код (.:/app) и закрыли бы его.
    POETRY_VIRTUALENVS_PATH=/opt/poetry-venvs

# Иначе debian-образ удаляет скачанные .deb и кэш apt пуст.
RUN rm -f /etc/apt/apt.conf.d/docker-clean

# poetry остаётся и в итоговом образе: сервисы запускаются через `poetry run`.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install poetry

WORKDIR /app


FROM base AS builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-root --no-ansi


FROM base AS runtime

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5

COPY --from=builder /opt/poetry-venvs /opt/poetry-venvs

COPY . .

CMD ["poetry", "run", "python", "-m", "src.bot"]
