"""
Поиск пользователя по тому, что написал в команде админ (или, позже, модератор): id
или @username. Общая точка на весь бот, не только creator_routers — модерация чатов
и «анкеты» (будущие модули) используют её же, а не заводят свою копию. До вынесения
сюда этот же разбор строки был в 12 местах, 11 из них в src/bot (не переписаны:
ban/reset/stats_edit/player_lookup/transfer сами резолвят query, им это не нужно).
"""

from src.bot.services import UserService
from src.database.models import User


async def find_user(user_service: UserService, query: str) -> User | None:
    """id или @username -> User, или None, если такого нет."""
    search: str | int = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
    return await user_service.get(search)
