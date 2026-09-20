from selfrot import BaseMiddleware
from selfrot.types import CallbackQuery, ChatMemberOwner, Message

from src.bot.repositories import ChatRepository, UserRepository
from src.bot.types.insert import ChatInsert

from ..context import AppContext


class SyncEntitiesMiddleware(BaseMiddleware[AppContext]):
    """
    Апсертит User/Chat на каждое сообщение, намеренно в СВОЕЙ сразу коммитящейся
    сессии, а не в сессии хендлера: иначе INSERT ... ON CONFLICT держал бы строку
    User залоченной до конца хендлера (см. src/bot/middlewares/sync_entity_middleware.py).

    Логика та же, что у SyncEntitiesService.sync(), но без aiogram-типов: сервис
    принимает aiogram.Update и Bot, а здесь нужны типы selfrot. Общая часть (вызовы
    репозиториев) продублирована сознательно, пока aiogram-версия жива.
    """

    async def pre_handle(self) -> bool:
        event = self.ctx.event

        async with self.ctx.session_factory() as session:
            if isinstance(event, (Message, CallbackQuery)) and event.user is not None:
                await UserRepository(session).upsert(
                    telegram_id=event.user.id,
                    first_name=event.user.first_name,
                    last_name=event.user.last_name,
                    username=event.user.username,
                    has_private_chat=True
                    if isinstance(event, Message) and event.chat.type == "private"
                    else None,
                )

            if isinstance(event, Message) and event.chat.type not in (
                "private",
                "channel",
            ):
                administrators = await self.ctx.bot.get_chat_administrators(
                    event.chat.id
                )
                creator = next(
                    (a for a in administrators if isinstance(a, ChatMemberOwner)),
                    administrators[0],
                )

                await ChatRepository(session).upsert(
                    ChatInsert(
                        telegram_id=event.chat.id,
                        title=event.chat.title,
                        username=event.chat.username,
                        creator_id=creator.user.id,
                    )
                )

            await session.commit()

        return True

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass
