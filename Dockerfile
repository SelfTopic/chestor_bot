FROM python:3.13-alpine

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev postgresql-dev build-base

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-root --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "-m", "src.bot"]