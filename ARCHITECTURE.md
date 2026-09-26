# Архитектура

Один бот в `src/bot` на [selfrotgram](https://github.com/SelfTopic/selfrotgram)
(импортируется как `selfrot`). Слои: роутеры (хендлеры) → сервисы (бизнес-логика) →
репозитории (SQLAlchemy-запросы) → БД. Роутер не ходит в репозиторий мимо сервиса там,
где сервис есть; сервис не знает про Telegram.

Игровой дизайн (что и почему) описан в `BATTLE_DESIGN.md` / `BATTLE_ENGINE.md` /
`ECONOMY.md` / `REGENERATION.md`. Этот файл только про то, где что лежит.

До перехода на selfrotgram бот был написан на aiogram 3. Его последнее состояние —
тег `aiogram-final`: комментарии «как у прода» ссылаются на поведение оттуда.

## Структура репозитория

```text
.
├── src/
│   ├── bot/              # бот целиком (см. ниже)
│   ├── config.py         # pydantic-settings, переменные окружения (см. «Три конфига»)
│   ├── database/models/  # SQLAlchemy-модели (общие для бота и миграций)
│   ├── assets/           # гифки/видео/шрифты (почти целиком вне git)
│   └── userbot_parser/   # отдельный парсер канала на Pyrogram, свой config/.env
├── migrations/           # Alembic (versions/ — и схема, и data-миграции seed-строк)
├── tests/                # см. «Тесты»
├── dialogs.json          # весь пользовательский текст ответов
└── *.md                  # дизайн-доки
```

## `src/bot/`

- **`__main__.py`** — `Dispatcher`: middlewares, корневой роутер, фоновые задачи
  (`NotificationTicker`, `DuelTicker`, `VideoWorker`), polling (`ENV=DEV`) или вебхук.
- **`context.py`** — `AppContext`, контекст одного апдейта. Все зависимости хендлера —
  его типизированные ленивые свойства (`ctx.ghoul_service`, `ctx.transfer_service`, …),
  плюс общие хелперы (`ctx.db_user()`, `ctx.addressee()`, `ctx.reply_gif()`, …).
- **`containers.py`** — DI-контейнер (`dependency-injector`): репозитории и сервисы,
  привязанные к сессии БД из `session_context`. Хендлеры его не видят, только `AppContext`.
- **`bot.py`**, **`logs.py`** — класс бота (прокси) и настройка логов.
- **`middlewares/`** — уровня диспетчера: `DatabaseMiddleware` (сессия на апдейт),
  `SyncEntitiesMiddleware` (апсерт `User`/`Chat` в отдельной сессии), `BanMiddleware`.
- **`routers/`** — только приём апдейтов и ответы. `RootRouter` в `routers/__init__.py`.
  - `common/` — команды, не завязанные на расу (профиль, баланс, переводы, вордли, RP,
    лотерея, аниме).
  - `ghoul_routers/` — механика гуля: голод, статы, кагуне, бои с мобами, дуэли (`duel/`),
    показ боя (`battle_text.py`, `battle_text_generator.py`).
  - `creator_routers/` — админ-команды (`ADMIN_IDS` проверяет middleware пакета).
  - `moderator_routers/` — приветствие/прощание/правила чата.
  - `chat_member_update_routers/` — вход и выход участников.
  - `rich.py`, `targeting.py`, `types.py`, `utils.py` — общее для нескольких областей.
- **`services/`** — бизнес-логика, без Telegram. Отправлять сообщения сервис может только
  через `Notifier` (`services/notify.py`, единственный модуль слоя, знающий про selfrot).
  - `battle_engine/core/` — **чистый домен боя** без БД и Telegram (`Fighter`, `Battle`,
    формулы). `battle_engine/engine.py` (`BattleEngine`) — мост: гуль → боец, мощь,
    готовность к бою; `mob.py` — мобы.
  - `battle.py` (`BattleService`) — бой целиком: участники, бой, здоровье после боя,
    награды, история, лок и стадии дуэли. Отдаёт итог одним объектом, роутер только показывает.
  - `admin/` — сервисы админ-команд; `ghoul_game/`, `wordle_game/`, `video/` — мини-игры
    и нарезка видео.
  - Заметные одиночные файлы: `ghoul.py` (статы/голод/смерть/поедание), `level_up.py`,
    `battle_record.py` (история боёв и `ActiveBattle`-лок), `notification_ticker.py`
    (уведомления о голоде/здоровье), `broadcast.py`, `quiz.py`.
- **`repositories/`** — только SQLAlchemy-запросы. Атомарные операции (`try_claim`,
  `atomic_update` с условным `WHERE ... RETURNING`) — устоявшийся паттерн вместо
  «прочитать, потом записать» везде, где есть риск гонки. `fight.py`, `user_names.py` —
  запросы, собирающие несколько чисел или имён одним запросом.
- **`exceptions/`**, **`types/`**, **`utils/`** — типизированные исключения по доменам,
  enum-подобные типы (`KaguneType`, `Race`), чистые функции расчётов.
- **Три разных «конфига», не перепутать**:
  - `src/config.py` — переменные окружения (`BOT_TOKEN`, `POSTGRES_*`, …).
  - `src/bot/config.py` — пути до папок с ассетами (`game_config`).
  - `src/bot/game_configs.py` — **балансные константы** (`BATTLE_CONFIG`, `MOB_CONFIG`,
    `DUEL_CONFIG`, …): сюда смотреть при вопросе «где число X».

Где лежит модуль, нужный только хендлерам, определяет правило раскладки из `CLAUDE.md`;
его проверяет `tests/test_layout.py`.

## Текст и данные вне кода

- **`dialogs.json`** — пользовательский текст (кроме rich-сообщений, они собираются из
  `InputRichBlock*`). `DialogService` перечитывает файл при изменении mtime.
- **`migrations/versions/`** — не только DDL: часть миграций — seed/data-апдейты (типы
  кулдаунов, их длительность).

## Поток запроса

1. Апдейт → `DatabaseMiddleware` (сессия на весь апдейт) → `SyncEntitiesMiddleware` →
   `BanMiddleware` → роутеры и их middlewares (доступ, «гуль жив») → хендлер.
2. Хендлер разбирает вход (`CommandArgs`, `CallbackPayload`), вызывает сервисы из `ctx`.
3. Сервис вызывает репозитории и другие сервисы.
4. Хендлер отвечает; `DatabaseMiddleware` коммитит сессию по выходу из хендлера.

**Важно:** в `after_handle` / `defer` и фоновых задачах сессия апдейта уже закрыта.
Тикеры открывают свою сессию через `session_factory` и сами собирают нужные сервисы
(см. `routers/ghoul_routers/duel/ticker.py`).

## Тесты

Один набор в `tests/`, общий `conftest.py`. Postgres настоящий: одноразовый контейнер
`postgres:16-alpine` на случайном порту, один на прогон и только если тесту нужна БД;
каждый тест получает чистую схему (`Base.metadata.create_all`, без Alembic, поэтому
seed-данные заводятся фикстурами). Telegram подменён фейковым HTTP-сервером (`FakeTelegram`).

- `tests/test_*.py` — бот целиком: апдейт на вход, вызовы Bot API на выходе.
- `tests/unit/` — домен и сервисы на одной сессии (`session`, `make_user`, `make_ghoul`).
- `tests/integration/` — несколько сессий сразу (гонки за баланс и т. п.).

## Развёртывание

`docker-compose.yml`: `postgres` → `migrations` (`alembic upgrade head`, разовый сервис,
он же собирает общий образ) → `bot` (`python -m src.bot`, ждёт оба через `depends_on`).
`pgadmin` — для ручной инспекции БД, `db_backup` / `rclone_backup` — ежедневный дамп и
синк в облако. Тестовый стенд — тот же compose в отдельном проекте
(`docker compose -p chestor_test …`) со своим `.env`.
