import logging

from selfrot import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.services import MobService
from src.bot.services.dialog import DialogService
from src.bot.session_services import SessionServices, session_context

from ....services.notify import SelfrotBotNotifier
from ....services.ticker import Ticker
from ...utils import quiet_edit
from .render import proposal_view, rename_view

logger = logging.getLogger(__name__)


class MarriageTicker(Ticker):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
        dialog_service: DialogService,
        mob_service: MobService,
        interval_seconds: float = 30.0,
    ) -> None:
        super().__init__(interval_seconds)
        self._session_factory = session_factory
        self._bot = bot
        self._dialog_service = dialog_service
        self._mob_service = mob_service

    async def tick(self) -> None:
        async with self._session_factory() as session:
            token = session_context.set(session)
            try:
                services = SessionServices(
                    self._dialog_service, SelfrotBotNotifier(self._bot), self._mob_service
                )
                family = services.family_service
                # (чат, сообщение, новый текст) для правки уже после коммита.
                edits: list[tuple[int, int | None, str]] = []
                for proposal in await family.expire_overdue():
                    state = await family.state(proposal.id)
                    assert state is not None
                    text, _ = await proposal_view(services, state, None)
                    edits.append((proposal.chat_id, proposal.message_id, text))
                for rename in await family.expire_overdue_renames():
                    text, _ = await rename_view(services, rename, None)
                    edits.append((rename.rename.chat_id, rename.rename.message_id, text))
                await session.commit()
            finally:
                session_context.reset(token)

        for chat_id, message_id, text in edits:
            if message_id is None:
                continue
            with quiet_edit("family ticker"):
                await self._bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML"
                )
