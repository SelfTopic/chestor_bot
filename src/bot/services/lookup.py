from src.bot.services import UserService
from src.database.models import User


async def find_user(user_service: UserService, query: str) -> User | None:
    search: str | int = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
    return await user_service.get(search)
