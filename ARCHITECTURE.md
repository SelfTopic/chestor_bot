# Архитектура Telegram Бота

## Общее описание
Бот построен по модульной архитектуре с четким разделением ответственности между компонентами.

## Структура проекта

### Core Components
```text
project/
├── src/
│ ├── bot/ # Основной модуль бота
│ ├── database/ # Модели и работа с БД
│ └── tests/ # Тесты (unit/integration)
```


### Детализация модулей

#### 1. **Routers** (`/src/bot/routers/`)
Обработчики сообщений и команд:
- `bot_router.py` - главный роутер
- `ghoul_routers/` - функционал гулей
- `moderator_routers/` - модерация
- `profile_router.py` - профили пользователей
- `error_router.py` - обработка ошибок

#### 2. **Services** (`/src/bot/services/`)
Бизнес-логика:
- `user.py` - управление пользователями
- `ghoul.py` - логика гулей
- `cooldown.py` - система кулдаунов
- `dialog.py` - работа с диалогами

#### 3. **Repositories** (`/src/bot/repositories/`)
Слой работы с данными:
- `user.py` - пользователи
- `ghoul.py` - гули
- `user_cooldown.py` - кулдауны

#### 4. **Middlewares** (`/src/bot/middlewares/`)
Промежуточное ПО:
- `database_middleware.py` - работа с БД
- `logging_middleware.py` - логирование
- `moderator_middleware.py` - проверка прав модератора

#### 5. **Database** (`/src/database/`)
Модели данных:
- `models/user.py` - модель пользователя
- `models/ghoul.py` - модель гуля
- `models/cooldown.py` - модель кулдаунов

#### 6. **Types** (`/src/bot/types/`)
Типы данных:
- `race.py` - расы
- `kagune.py` - кагуне
- `register_ghoul.py` - регистрация

## Поток данных
1. **Вход** → Middleware → Router → Service → Repository → Database
2. **Выход** → Service → Router → Пользователь

## Зависимости
- **DI**: Используется dependency injection (`containers.py`)
- **Миграции**: Alembic (`/migrations/`)
- **Тестирование**: Pytest (`/tests/`)
- **Конфигурация**: Poetry (`pyproject.toml`)

## Запуск и развертывание
- Docker-контейнеризация
- Environment variables (`.env`)
- Миграции через Alembic