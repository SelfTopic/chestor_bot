import logging

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.services import MobService
from src.bot.services.dialog import DialogService
from src.bot.session_services import SessionServices, session_context

from ....services.notify import SelfrotBotNotifier
from ....services.ticker import Ticker
from .render import proposal_view

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
                expired = await services.family_service.expire_overdue()
                views = []
                for proposal in expired:
                    state = await services.family_service.state(proposal.id)
                    assert state is not None
                    views.append((proposal, await proposal_view(services, state, None)))
                await session.commit()
            finally:
                session_context.reset(token)

        for proposal, (text, _) in views:
            if proposal.message_id is None:
                continue
            try:
                await self._bot.edit_message_text(
                    chat_id=proposal.chat_id,
                    message_id=proposal.message_id,
                    text=text,
                    parse_mode="HTML",
                )
            except TelegramAPIError:
                logger.warning("marriage %s: failed to mark the invite expired", proposal.id)
