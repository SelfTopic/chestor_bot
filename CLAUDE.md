# chestor_bot

Telegram-бот по «Токийскому гулю»: игроки, гули, кагуне, бои, экономика, RP-команды.
Postgres + SQLAlchemy (async), миграции Alembic, запуск в Docker Compose.

Бот один: `src/bot/` на selfrotgram. Раньше он был написан на aiogram 3; последнее
состояние той версии — тег `aiogram-final` (`git show aiogram-final:src/bot/...`).
Кода на aiogram и зависимости от него в репозитории нет, не возвращай их.

Репозиторий публичный: никаких токенов, паролей, `.env` и файлов сессий в коммитах.

## Поведение

Бот повторяет поведение aiogram-версии («прода»): те же команды, тексты, ответы и порядок
роутеров (`RootRouter` повторяет `include_routers` прода). Странности прода сохранены и
помечены комментарием «как у прода»; сверять их — по тегу `aiogram-final`. Если такую
странность исправляешь (например, разделив команду на два хендлера), пиши об этом в
комментарии и в сообщении коммита, а не чини молча.

## selfrotgram

Библиотека владельца проекта, импортируется как `selfrot`. Прежде чем писать хендлер, прочитай:

- https://github.com/SelfTopic/selfrotgram/blob/main/docs/from-aiogram.md — соответствия aiogram → selfrot
- https://github.com/SelfTopic/selfrotgram/blob/main/docs/examples.md и папку `examples/`
  (`examples/chat_members.py`, `examples/chestor_routers/` написаны прямо под этот бот)

Пользуйся возможностями библиотеки, а не разбирай руками: `CommandArgs` / `Rest` /
`CommandArgsError` + `on_error` хендлера, `CallbackPayload`, `after_handle` / `defer` для
долгой работы, `Bot.defaults`, фильтры `Has*`, `TextStartswith`, `AnyCommand`, `Reply[T]`.
Перед выбором фильтра посмотри полный список имён в `selfrot.filter`, а не ищи по догадке.
Если в библиотеке чего-то не хватает, не обходи это хаком: опиши пробел владельцу.

## Устройство бота

Карта папок — в `ARCHITECTURE.md`. Правила:

**Зависимости — через `AppContext`** (`context.py`). Сервисы там — типизированные ленивые
`cached_property`, один экземпляр на апдейт: `self.ctx.transfer_service`, `self.ctx.ghoul_service`.
Хендлеры **никогда** не обращаются к `ctx.container`. Нужен новый сервис — добавь свойство
в `AppContext` (и провайдер в `containers.py`, если сервис собирается контейнером).

- Сервисы привязаны к сессии БД, которую ставит `DatabaseMiddleware`. В `after_handle` /
  `defer` сессия уже закрыта, session-bound сервисы там не использовать.
- `on_error` хендлера выполняется после сброса сессии: никаких `ctx.*_service` внутри,
  даже для текста ошибки. Такой текст считай константой модуля заранее.
- Общие хелперы для любых роутеров: `ctx.db_user()`, `ctx.addressee()` (кому адресована
  команда: ответ или @username/id), `ctx.answer_gif()` / `ctx.reply_gif()` (кэш file_id
  с повтором при устаревшем id), `ctx.cooldown_remaining()`, `ctx.first_names(ids)` (имена
  игроков одним запросом, а не `user_service.get` в цикле).

**Запросы — в `repositories/`.** Если нужно несколько чисел или имён, это один запрос в
репозитории (`repositories/fight.py`, `repositories/user_names.py`), а не цикл в сервисе.

**Бои — `ctx.battle_service`** (`services/battle.py`): участники одним запросом, гуль →
боец, бой, здоровье после боя, награды, история, лок и стадии дуэли. Возвращает итог
одним объектом (`DuelFight`, `DuelOutcome`, `MobFight`, внутри `FightReport` для
показа), а роутер только отправляет: `battle_text.BattleMessage` (rich, иначе текст).
Мост к движку (гуль → боец, мощь, готовность к бою) — `ctx.battle_engine`
(`BattleEngine`, `services/battle_engine/engine.py`). `battle_engine/core/` — чистый
домен боя без БД и Telegram.

**Telegram — не в сервисах.** Сервис не принимает `Message` и не шлёт сообщения сам.
Если сервису нужно отправлять (рассылка, level up, тикер уведомлений), он получает
`Notifier` из `services/notify.py`: это единственное место в `services/`, где импортируется
`selfrot`. Всё, что собирает Telegram-типы (клавиатуры, rich-сообщения), живёт в `routers/`.

**Где что лежит — правило без исключений** (его проверяет `tests/test_layout.py`):

- **Слои по ролям** — корень `src/bot` (`context.py`, `bot.py`, `containers.py`, `config.py`,
  `game_configs.py`, `logs.py`), `services/`, `repositories/`, `middlewares/`, `types/`,
  `exceptions/`, `utils/`. Сервис глобален, потому что он сервис, сколько бы роутеров им ни
  пользовалось. Слои не импортируют `routers/`; собирает всё только `__main__.py`.
- **Всё, что нужно только хендлерам** (миксины, фильтры, типы сообщений, хелперы отправки),
  лежит в самой глубокой общей папке тех, кто это импортирует: нужен одному пакету — в пакете
  (`common/transfer/flow.py`), нескольким пакетам области — в папке области
  (`ghoul_routers/battle_text.py`), нескольким областям — в `routers/` (`routers/types.py`,
  `routers/targeting.py`, `routers/rich.py`, `routers/utils.py`). Модуль корня, который
  нужен только роутерам, тоже уезжает в `routers/`.
- **Не импортировать вбок и внутрь чужого пакета.** Понадобилось соседу — поднять до общей
  папки. Родитель берёт из пакета то, что пакет выставил в `__init__.py`, а не лезет в его
  модули (так `routers/__init__.py` берёт роутеры `common`).
- Тесты пользователями не считаются. Перенос — `git mv` и правка импортов, логика не меняется.

**Раскладка роутеров** (образец — `routers/common/role_play/`):

- Роутер длиннее ~150 строк становится пакетом (`flow.py`, `commands.py`, `handlers.py`, …).
- Фильтр или middleware, нужный одному роутеру, живёт в его пакете.
- Тексты usage и ошибок — атрибуты хендлера; тексты игры — `dialogs.json` через `dialog_service`.
- Хелпер, нужный один раз, — метод хендлера. Отправка, общая для пакета, — модуль вроде `sending.py`.
- Класс `CommandArgs` стоит прямо над своим хендлером.

**Команды «ответом или по @username/id»** — всегда два хендлера (`XRepliedHandler` с
`HasReplyUser()` и `XHandler` с `~HasReplyUser()`), а не один с плавающими аргументами:
у прода на этом были реальные баги (`/ban_bot`, `/set_stat`). Используй миксины из
`routers/targeting.py` (`RepliedTargetHandler`, `ExplicitTargetHandler`, `TargetArgs`);
конкретный хендлер реализует только `perform(telegram_id, args)`.
Важно: миксины намеренно не наследуют `MessageHandler[...]`. Каждый хендлер явно пишет
его вторым базовым классом:
`class KillGhoulHandler(ExplicitTargetHandler[KillGhoulArgs], MessageHandler[AppContext[TextMessage]])`.
Проверка `DefinitionError` в selfrot смотрит только на прямые базовые классы, и через
generic-миксин она молча отключилась бы.

**Запуск.** Сервис `bot` в `docker-compose.yml` запускает `python -m src.bot`, токен —
`BOT_TOKEN`. `ENV=DEV` — polling, иначе вебхук на 8999 (`WEBHOOK_URL`, `WEBHOOK_SECRET`).
Тестовый стенд — тот же сервис в отдельном проекте (`docker compose -p chestor_test …`)
со своим `.env`: токен тестового бота. Как поднять бота в облачной сессии и проверить
изменения вживую — `docs/dev-session.md`.

## Проверки

Перед каждым коммитом всё должно быть чисто:

```bash
ruff check src/bot tests
pyright src/bot tests                      # режим standard
selfrot check --strict src.bot.__main__:Dispatcher
python -m pytest tests
```

- Тестам нужен Docker: общий `tests/conftest.py` поднимает `postgres:16-alpine` на
  случайном порту (один на прогон, только если тесту нужна БД), а Telegram подменён
  фейковым HTTP-сервером (`FakeTelegram`).
- `tests/test_*.py` — бот целиком (апдейт → вызовы Bot API). `tests/unit/` — домен и
  сервисы на одной сессии, `tests/integration/` — несколько сессий сразу (гонки).
- Фикстуры: `send` (отправить текст, получить ответы бота), `feed`, `telegram`
  (`bodies(method)`, `fail_next(...)`, `set_file(...)`), `session_factory`,
  `message_update` / `callback_update` / `chat_member_update`, `admin_dict` / `owner_dict` /
  `member_dict`, `button_data`, `settle`; для `unit/` и `integration/` — `engine`,
  `session`, `user_repo`, `ghoul_repo`, `make_user`, `make_ghoul`.
- Новый тест не повторяет сценарий, который уже проверяет другой тест, на любом уровне.
- `GhoulService.get()` считает `telegram_id <= 666000` внутренним id гуля, поэтому в тестах
  гулей бери telegram_id больше, например `700001`.
- Медиа (`src/assets`: гифки, видео) почти целиком не в git. В чистом клоне тесты, которым
  нужен реальный файл (лотерея: `TestDep::test_bet_changes_balance_and_result_arrives_later`),
  падают, потому что файла нет. Это ожидаемо.

Типизация — pyright в режиме standard. Значения из нетипизированных источников (`dict[str, Any]`,
JSON, `.get()`) сужай через `isinstance` / `assert`, прежде чем передавать в типизированный код.

## Открытые задачи

- `dependency-injector`: после ухода aiogram контейнер — просто список фабрик под
  `AppContext`. Можно собирать сервисы прямо в `AppContext` и убрать зависимость.
- Модули, которые никто не импортирует (мёртвые ещё до ухода aiogram):
  `utils/data_parser.py`, `utils/race_calculate.py`, `services/duration_parser.py`.
  Решение за владельцем. `utils/generate_lottery_video.py` не из их числа: это скрипт
  (`python -m src.bot.utils.generate_lottery_video`), генерирует видео для лотереи
  через `services/lottery_video_genertor.py`.

## Git

Коммить логичными шагами: один роутер или одна область — один коммит, и каждый коммит
проходит проверки выше. Сообщения — conventional commits на английском
(`feat(duel): ...`, `fix: ...`).
