"""Роутер PvP-дуэлей - от команды до записи в историю. Разбит на
несколько файлов вместо одного большого модуля:

- `invite_router.py` - шаг 1, команда "дуэль" (приглашение).
- `duel_process_router.py` - шаги 2/3/5, обработка нажатий кнопок
  (согласие/всерьёз-фора/выбор победителя).
- `fight.py` - общая логика "разыграть бой"/"применить исход",
  используется и живыми колбэками, и фоновыми таймаутами.
- `background.py` - сами фоновые таймауты (`asyncio.create_task`).
- `services.py` - сборка сервисов от свежей сессии (для фоновых задач).
- `keyboards.py` - inline-клавиатуры.
- `callback_data.py` - формат callback_data и его разбор.

Весь боевой движок и персистентность (`BattleService`, `BattleRecordService`,
`ActiveBattle`/`Battle`) уже готовы - этот пакет только связывает их в
реальный Telegram-флоу. См. докстринги отдельных файлов для деталей
конкретных шагов."""

from aiogram import Router

from .callback_data import parse_duel_callback_payload
from .duel_process_router import router as duel_process_router
from .invite_router import router as invite_router

router = Router(name="duel")
router.include_routers(invite_router, duel_process_router)

__all__ = ["router", "parse_duel_callback_payload"]
