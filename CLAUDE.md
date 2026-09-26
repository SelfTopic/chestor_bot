# chestor_bot

Telegram-бот по «Токийскому гулю»: игроки, гули, кагуне, бои, экономика, RP-команды.
Postgres + SQLAlchemy (async), миграции Alembic, запуск в Docker Compose.

В репозитории два бота:

- `src/bot/` — **прод** на aiogram 3. Это эталон поведения: его читаем, но не меняем.
- `src/selfrot_bot/` — **порт** на selfrotgram (ветка `feature/port-to-selfrotgram`).
  Вся новая работа идёт здесь. Новые модули тоже пишутся сразу в порте, а не в `src/bot`.

Репозиторий публичный: никаких токенов, паролей, `.env` и файлов сессий в коммитах.

## Главное правило порта

**Поведение 1:1 с продом**: те же команды, тексты, ответы и порядок роутеров (`RootRouter`
повторяет `include_routers` прода). Странности прода сохраняем и помечаем комментарием
«как у прода», а не чиним молча. Если прод-баг всё же исправлен (например, тем, что команда
разделена на два хендлера), это пишется в комментарии и в сообщении коммита.

## selfrotgram

Библиотека владельца проекта, импортируется как `selfrot`. Прежде чем писать хендлер, прочитай:

- https://github.com/SelfTopic/selfrotgram/blob/main/docs/from-aiogram.md — соответствия aiogram → selfrot
- https://github.com/SelfTopic/selfrotgram/blob/main/docs/examples.md и папку `examples/`
  (`examples/chat_members.py`, `examples/chestor_routers/` написаны прямо под этот порт)

Пользуйся возможностями библиотеки, а не разбирай руками: `CommandArgs` / `Rest` /
`CommandArgsError` + `on_error` хендлера, `CallbackPayload`, `after_handle` / `defer` для
долгой работы, `Bot.defaults`, фильтры `Has*`, `TextStartswith`, `AnyCommand`, `Reply[T]`.
Перед выбором фильтра посмотри полный список имён в `selfrot.filter`, а не ищи по догадке.
Если в библиотеке чего-то не хватает, не обходи это хаком: опиши пробел владельцу.

## Устройство порта

**Зависимости — через `AppContext`** (`context.py`). Сервисы там — типизированные ленивые
`cached_property`, один экземпляр на апдейт: `self.ctx.transfer_service`, `self.ctx.ghoul_service`.
Хендлеры **никогда** не обращаются к `ctx.container`. Нужен новый сервис — добавь свойство
в `AppContext`.

- Сервисы привязаны к сессии БД, которую ставит `DatabaseMiddleware`. В `after_handle` /
  `defer` сессия уже закрыта, session-bound сервисы там не использовать.
- `on_error` хендлера выполняется после сброса сессии: никаких `ctx.*_service` внутри,
  даже для текста ошибки. Такой текст считай константой модуля заранее.
- Общие хелперы для любых роутеров: `ctx.db_user()`, `ctx.addressee()` (кому адресована
  команда: ответ или @username/id), `ctx.answer_gif()` / `ctx.reply_gif()` (кэш file_id
  с повтором при устаревшем id), `ctx.cooldown_remaining()`, `ctx.first_names(ids)` (имена
  игроков одним запросом, а не `user_service.get` в цикле).

**Переиспользуй прод.** Репозитории, сервисы и доменная логика из `src/bot`, которые не
завязаны на aiogram, импортируются как есть. В порте переписывается только то, что трогает
Telegram. Запросы, которых у прод-репозиториев нет (например, несколько чисел одним
запросом вместо нескольких), живут в `src/selfrot_bot/repositories/`.

**Бои — `ctx.battle_service`** (`services/battle.py`): участники одним запросом, гуль →
боец, бой, здоровье после боя, награды, история, лок и стадии дуэли. Возвращает итог
одним объектом (`DuelFight`, `DuelOutcome`, `MobFight`, внутри `FightReport` для
показа), а роутер только отправляет: `battle_text.BattleMessage` (rich, иначе текст).
Прод-мост к движку (гуль → боец, мощь, готовность к бою) — `ctx.battle_engine`.

**Telegram — не в сервисах.** Сервис не принимает `Message` и не шлёт сообщения сам.
Если сервису нужно отправлять (рассылка, level up, тикер уведомлений), он получает
`Notifier` из `services/notify.py`: это единственное место в `services/`, где импортируется
`selfrot`.

**Где что лежит — правило без исключений** (его проверяет `tests_selfrot/test_layout.py`):

- **Слои по ролям** — корень порта (`context.py`, `bot.py`, `media.py`), `services/`,
  `repositories/`, `middlewares/`. Сервис глобален, потому что он сервис, сколько бы роутеров
  им ни пользовалось. Слои не импортируют `routers/`; собирает всё только `__main__.py`.
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
у прода на этом реальные баги (`/ban_bot`, `/set_stat`). Используй миксины из `routers/targeting.py`
(`RepliedTargetHandler`, `ExplicitTargetHandler`, `TargetArgs`); конкретный хендлер
реализует только `perform(telegram_id, args)`.
Важно: миксины намеренно не наследуют `MessageHandler[...]`. Каждый хендлер явно пишет
его вторым базовым классом:
`class KillGhoulHandler(ExplicitTargetHandler[KillGhoulArgs], MessageHandler[AppContext[TextMessage]])`.
Проверка `DefinitionError` в selfrot смотрит только на прямые базовые классы, и через
generic-миксин она молча отключилась бы.

**Запуск.** Порт — это и есть бот: сервис `bot` в `docker-compose.yml` запускает
`src.selfrot_bot`, токен — `BOT_TOKEN`. `ENV=DEV` — polling, иначе вебхук на 8999
(`WEBHOOK_URL`, `WEBHOOK_SECRET`). Тестовый стенд — тот же сервис в отдельном проекте
(`docker compose -p chestor_test …`) со своим `.env`: токен тестового бота.

## Проверки

Перед каждым коммитом всё должно быть чисто:

```bash
ruff check src/bot tests
pyright src/bot tests                      # режим standard
selfrot check --strict src.bot.__main__:Dispatcher
python -m pytest tests
```

- `tests_selfrot/` — тесты порта. Им нужен Docker: поднимается `postgres:16-alpine` на
  случайном порту, а Telegram подменён фейковым HTTP-сервером (`FakeTelegram`).
  `tests/` — тесты прода, там conftest автоматически поднимает Postgres для каждого теста;
  тесты порта туда не класть.
- Фикстуры в `tests_selfrot/conftest.py`: `send` (отправить текст, получить ответы бота),
  `feed`, `telegram` (`bodies(method)`, `fail_next(...)`, `set_file(...)`), `session_factory`,
  `message_update` / `callback_update` / `chat_member_update`, `admin_dict` / `owner_dict` /
  `member_dict`, `button_data`, `settle`.
- `GhoulService.get()` считает `telegram_id <= 666000` внутренним id гуля, поэтому в тестах
  гулей бери telegram_id больше, например `700001`.
- Медиа (`src/assets`: гифки, видео) почти целиком не в git. В чистом клоне тесты, которым
  нужен реальный файл (например, лотерея), падают, потому что файла нет.

Типизация — pyright в режиме standard. Значения из нетипизированных источников (`dict[str, Any]`,
JSON, `.get()`) сужай через `isinstance` / `assert`, прежде чем передавать в типизированный код.

## Что осталось портировать

Ничего: порт `src/bot` завершён, `src/bot/routers/ghoul_routers/` перенесён целиком.
Бои с мобом и дуэли считает `services/battle.py`, показывают `ghoul_routers/mob_battle.py`,
`duel/fight.py` и `battle_text.py`. Таймауты дуэлей ведёт
`DuelTicker` (`ghoul_routers/duel/ticker.py`), задача уровня диспетчера, как
`NotificationTicker`. Новая работа идёт уже как новые модули порта.

## Текущая задача: удаление aiogram (ветка `feature/drop-aiogram`)

Цель: в репозитории не остаётся кода на aiogram и зависимости от него, весь бот живёт
в одной папке `src/bot` (слои `services/`, `repositories/` и т. д. — по одному на бота,
без деления на «прод» и «порт»). Прод-эталон после удаления — тег `aiogram-final`:
поведение сверяем с ним (`git show aiogram-final:src/bot/...`).

На время задачи правило «прод-код в коммитах не меняется» не действует: `src/bot`
удаляется и переписывается. Остальные правила (поведение 1:1, проверки перед каждым
коммитом, раскладка) действуют. `dependency-injector` и `containers.py` остаются —
это отдельная задача.

Этапы (отмечай `✓` и коммить вместе с работой):

1. ✓ Удалить оболочку прода: `src/bot/{routers,filters,middlewares,__main__.py}`, прод-версии
   сервисов, у которых в порте есть замена (`level_up`, `admin/broadcast`,
   `notification_ticker`, `sync_entity`), и их тесты.
2. ✓ Отвязать от aiogram сервисы, которые использует порт: `containers.py` (провайдер `bot`),
   `ghoul.get`, `user.upsert`, `media` (скачивание), `stat_upgrade.build_message`, методы
   отправки в `coffee` / `lottery`, `battle_engine/text_generator` (→ selfrot-типы, к роутерам).
3. ✓ Удалить `aiogram` из `pyproject.toml`, `poetry lock`.
4. ✓ Слить `src/selfrot_bot` в `src/bot` (`git mv` + импорты), прод-мост `BattleService`
   движка переименовать в `BattleEngine`, обновить `test_layout.py`, compose, `selfrot check`.
5. ✓ Тесты прода: нужные (домен, репозитории, гонки) перенести, дубли и ненужные удалить;
   `tests_selfrot/` → `tests/`.
6. Документация: этот файл, `README.md`, `ARCHITECTURE.md`, `Dockerfile`; удалить `docs/port-plan.md`.

## Git

Коммить логичными шагами: один роутер или одна область — один коммит, и каждый коммит
проходит проверки выше. Сообщения — conventional commits на английском
(`feat(selfrot): port ...`). Прод-код (`src/bot`) в коммитах порта не меняется.
