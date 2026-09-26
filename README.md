# CheStor Bot

Телеграм-бот по фандому «Токийский гуль»: гули со статами, голодом и
кагуне, естественная регенерация и смерть, прокачка уровней и полноценный
боевой движок (дуэли, бои с мобами, засады во время еды). Подробный
игровой дизайн и обоснование решений - в `BATTLE_DESIGN.md`/
`BATTLE_ENGINE.md`/`ECONOMY.md`/`REGENERATION.md` (см. раздел
«Документация» ниже).

Текущая версия - `1.0.0`: игровой цикл целиком закрыт (голод → смерть →
регенерация → прокачка → бои).

## Стек

- Python 3.11-3.14, [Poetry](https://python-poetry.org/) для зависимостей
- [selfrotgram](https://github.com/SelfTopic/selfrotgram) (`selfrot`) - Telegram Bot API
- SQLAlchemy 2 (async) + PostgreSQL, миграции - Alembic
- `dependency-injector` - DI-контейнер (`src/bot/containers.py`), хендлеры берут
  зависимости из `AppContext` (`src/bot/context.py`)
- Docker/Docker Compose - для запуска Postgres/бота/бэкапов

## Быстрый старт (Docker)

```bash
cp .env.example .env   # заполнить BOT_TOKEN и остальные переменные
docker compose up -d --build
```

Compose поднимает Postgres, накатывает миграции (сервис `migrations`) и
только потом запускает бота - руками ничего дополнительно катить не
нужно. `pgadmin` доступен на `:5050` для инспекции БД.

## Локальная разработка (без Docker)

```bash
poetry install
cp .env.example .env    # POSTGRES_HOSTNAME=localhost, если Postgres локальный
poetry run alembic upgrade head
poetry run python -m src.bot
```

## Тесты и линт

Тесты поднимают одноразовый Postgres в Docker сами (`tests/conftest.py`) -
Docker должен быть доступен, отдельно поднимать БД не нужно. Telegram в тестах
подменён фейковым HTTP-сервером.

```bash
poetry run ruff check src/bot tests
poetry run pyright src/bot tests
poetry run selfrot check --strict src.bot.__main__:Dispatcher
poetry run pytest tests -q
```

## Документация

- [`ARCHITECTURE.md`](ARCHITECTURE.md) - структура проекта, слои
  (роутеры/сервисы/репозитории).
- [`BATTLE_DESIGN.md`](BATTLE_DESIGN.md) - игровой дизайн целиком: голод,
  регенерация, смерть, прокачка, экономика.
- [`BATTLE_ENGINE.md`](BATTLE_ENGINE.md) - боевой движок в деталях
  (формулы урона/уклонения, дуэли, бои с мобами).
- [`REGENERATION.md`](REGENERATION.md) - модель регенерации HP в бою.
- [`ECONOMY.md`](ECONOMY.md) - источники и стоки CheSton/RC-клеток.

Эти доки - источник истины по игровым решениям и живут вместе с кодом
(обновляются в том же PR/мердже, что и реализация), а не отдельно от
него.
