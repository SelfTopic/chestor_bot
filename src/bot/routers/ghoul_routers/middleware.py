from selfrot import BaseMiddleware
from selfrot.types import CallbackQuery, Message

from ...context import AppContext

_GROW_KAGUNE_BYPASS = "растить кагуне"


class GhoulMiddleware(BaseMiddleware[AppContext]):
    """
    Гейт всего ghoul_routers: без гуля доступа нет (кроме команды "растить кагуне" —
    ей и предстоит завести гуля), мёртвому гулю — тоже нет (единственный его выход
    остаётся та же "растить кагуне", см. BATTLE_DESIGN.md). У прода апдейт проверяется
    как Message ИЛИ CallbackQuery; для остальных типов (сюда они не должны попадать,
    у ghoul_routers нет для них хендлеров) прод тихо роняет апдейт — pre_handle делает
    то же самое, просто не пропуская дальше.
    """

    async def pre_handle(self) -> bool:
        event = self.ctx.event
        if not isinstance(event, (Message, CallbackQuery)):
            return False

        if (
            isinstance(event, Message)
            and event.text
            and event.text.lower() == _GROW_KAGUNE_BYPASS
        ):
            return True

        user = self.ctx.user
        if user is None:
            return False

        ghoul = await self.ctx.ghoul_service.get(find_by=user.id)
        if ghoul is None:
            await event.answer(
                "Ты не гуль. Используй команду 'Растить кагуне' чтобы стать гулем."
            )
            return False

        if ghoul.is_dead:
            await event.answer(self.ctx.dialog_service.text(key="dead_ghoul_reply"))
            return False

        return True

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
