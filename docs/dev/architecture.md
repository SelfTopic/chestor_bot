# Архитектура

Один бот в `src/bot` на [selfrotgram](https://github.com/SelfTopic/selfrotgram)
(импортируется как `selfrot`). Слои: роутеры (хендлеры) → сервисы (бизнес-логика) →
репозитории (SQLAlchemy-запросы) → БД. Роутер не ходит в репозиторий мимо сервиса там,
где сервис есть; сервис не знает про Telegram.

Игровой дизайн (что и почему) описан в `docs/design/`. Этот файл только про то, где что
лежит.

До перехода на selfrotgram бот был написан на aiogram 3. Его последнее состояние —
тег `aiogram-final`: с ним сверяется поведение бота.

## Структура репозитория

```text
.
├── src/
│   ├── bot/              # бот целиком (см. ниже)
│   ├── config.py         # pydantic-settings, переменные окружения (см. «Три конфига»)
│   ├── database/models/  # SQLAlchemy-модели (общие для бота и миграций)
│   ├── assets/           # гифки/видео/шрифты (почти целиком вне git)
│   └── userbot_parser/   # юзербот на Pyrogram: серии аниме и эдиты для «1000-7», свой .env
├── migrations/           # Alembic (versions/ — и схема, и data-миграции seed-строк)
├── tests/                # см. «Тесты»
├── docs/
│   ├── dev/              # этот файл, живая проверка в облачной сессии
│   └── design/           # игровой дизайн: журналы решений
├── README.md
└── CLAUDE.md             # правила для кода
```

## `src/bot/`

- **`__main__.py`** — `Dispatcher`: middlewares, корневой роутер, фоновые задачи
  (`tasks = TASKS`), `VideoWorker`, polling (`ENV=DEV`) или вебхук.
- **`tasks/`** — фоновые задачи selfrot (`BaseTask`, `Every`): истечение дуэлей и голосований
  семьи, уведомления, сроки модерации, сброс статистики, обновление yt-dlp. Собирающий слой,
  как `__main__.py`: берёт роутеры из `routers/__init__.py`, импортирует его только `__main__.py`.
- **`context.py`** — `AppContext`, контекст одного апдейта. Все зависимости хендлера —
  его типизированные ленивые свойства (`ctx.ghoul_service`, `ctx.transfer_service`, …),
  плюс общие хелперы (`ctx.say()`, `ctx.text()`, `ctx.db_user()`, `ctx.addressee()`, …).
- **`session_services.py`** — `SessionServices`: репозитории и сервисы на текущей сессии БД
  (`session_context`), каждый — `cached_property`. `AppContext` её наследует. Процессные сервисы создаёт `Dispatcher` и передаёт полями `AppContext`.
- **`bot.py`**, **`logs.py`** — класс бота (прокси) и настройка логов.
- **`middlewares/`** — уровня диспетчера: `DatabaseMiddleware` (сессия на апдейт),
  `SyncEntitiesMiddleware` (апсерт `User`/`Chat` в отдельной сессии), `BanMiddleware`.
- **`routers/`** — только приём апдейтов и ответы. `RootRouter` в `routers/__init__.py`.
  - `common/` — команды, не завязанные на расу (профиль, баланс, переводы, вордли, RP,
    лотерея, аниме, `fun/`: «бот выбери/кто/число», «бот найди», калькулятор).
    `link_media_router.py` отвечает роликом на ссылку TikTok/YouTube, `userbot_inbox.py`
    принимает от юзербота серии аниме и эдиты, `edits_router.py` отвечает эдитом на «1000-7»,
    `music/` ищет, распознаёт («шазам») и присылает песни, `marriage/` — браки и семьи
    (предложение, согласия в группе и в личке по ссылке, «семья», «развод», истечение срока — `expiry.py`). `roast_router.py` стоит
    последним в `RootRouter`: огрызается нейросетью на то, что не забрала ни одна команда.
  - `ghoul_routers/` — механика гуля: голод, статы, кагуне, бои с мобами, дуэли (`duel/`),
    показ боя (`battle_text.py`, `battle_text_generator.py`).
  - `creator_routers/` — админ-команды (`ADMIN_IDS` проверяет middleware пакета).
  - `moderator_routers/` — модерация чата (модератор — админ Telegram с нужным правом):
    `punishments/` — мут, бан, кик и их снятие, `settings/` — сроки по умолчанию, голос
    модерации и привязка чата админов, куда уходит каждое действие и изменение настроек;
    приветствие/прощание/правила чата.
  - `chat_member_update_routers/` — вход и выход участников; ведут учёт участников чата
    (`ChatParticipant`, сообщения в группе считает `SyncEntitiesMiddleware`).
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
    (уведомления о голоде/здоровье), `broadcast.py`, `quiz.py`, `family.py` (семьи:
    предложение брака, согласия, свадьба, развод).
  - `moderation/` — модерация чатов: настройки чата (`moderation_settings`) и журнал
    действий (`moderation_actions`). Сам Telegram (мут, бан) зовут роутеры.
  - `llm.py` — клиент нейросети Cloud.ru Foundation Models (API как у OpenAI), общий для
    огрызаний и поиска.
  - `roast/` — огрызания через нейросеть:
    `RoastService` (состояние споров, лимиты, фильтр, журнал `roast_log`) и `prompts/` —
    характер, примеры и обращения в файлах, которые правятся без кода.
  - `link_media/` — видео по ссылкам TikTok/YouTube: поиск ссылок (`links.py`), выбор
    формата под лимит Bot API (`formats.py`), yt-dlp, gallery-dl для фотокаруселей и
    запасной tikwm (`downloader.py`),
    `LinkMediaService` (параллельность, временная папка, кэш `file_id` по id поста в
    `link_media_cache` своими сессиями) и `MediaToolsUpdater` (суточное
    обновление yt-dlp и gallery-dl в их venv).
  - `media_tools.py` — запуск yt-dlp/gallery-dl/ffmpeg подпроцессом и их суточное обновление,
    общее для видео по ссылкам и песен.
  - `music/` — «песня» и «шазам»: поиск треков на YouTube и скачивание звука с обложкой
    (`search.py`), распознавание песни через shazamio (`recognize.py`),
    `MusicService` (параллельность, кэш `file_id` в `music_tracks`).
  - `player_docs/` — документация для игроков: разделы из `docs/players/*.md` (`pages.py`) и
    их публикация rich-постами в канал с правкой изменившихся (`service.py`).
  - `search/` — «бот найди»: поиск Tavily (`tavily.py`) и краткий ответ модели по найденным
    фрагментам; `SearchService` держит общий дневной лимит и кулдаун игрока в памяти,
    инструкция модели — `prompts/system.md`.
- **`repositories/`** — только SQLAlchemy-запросы. Атомарные операции (`try_claim`,
  `atomic_update` с условным `WHERE ... RETURNING`) — устоявшийся паттерн вместо
  «прочитать, потом записать» везде, где есть риск гонки. `fight.py`, `user_names.py` —
  запросы, собирающие несколько чисел или имён одним запросом. `wallet.py` — кошелёк игрока:
  счёт семьи у её члена, личный баланс у свободного; `family.py` — семьи и предложения брака.
- **`dialogs/`** — тексты ответов: `*.yaml` и сгенерированное из них дерево `Dialogs`
  (`tree.py`, `python -m src.bot.dialogs.generate`), через которое код их берёт.
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

- **`src/bot/dialogs/*.yaml`** — пользовательский текст (кроме rich-сообщений, они собираются
  из `InputRichBlock*`). `DialogService` перечитывает файлы при изменении mtime; правка,
  которая не сходится с деревом `Dialogs`, не применяется.
- **`migrations/versions/`** — не только DDL: часть миграций — seed/data-апдейты (типы
  кулдаунов, их длительность).

## Поток запроса

1. Апдейт → `DatabaseMiddleware` (сессия на весь апдейт) → `SyncEntitiesMiddleware` →
   `BanMiddleware` → роутеры и их middlewares (доступ, «гуль жив») → хендлер.
2. Хендлер разбирает вход (`CommandArgs`, `CallbackPayload`), вызывает сервисы из `ctx`.
3. Сервис вызывает репозитории и другие сервисы.
4. Хендлер отвечает; `DatabaseMiddleware` коммитит сессию по выходу из хендлера.

**Важно:** в `after_handle` / `defer` сессия апдейта уже закрыта. Фоновая задача (`tasks/`)
получает свою сессию от тех же middleware, что и апдейт.

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
