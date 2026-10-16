from selfrot import Bot

from src.bot.session_services import SessionServices

from ...utils import quiet_edit
from .render import proposal_view, rename_view


async def expire_overdue_votes(services: SessionServices, bot: Bot) -> None:
    family = services.family_service
    edits: list[tuple[int, int | None, str]] = []
    for proposal in await family.expire_overdue():
        state = await family.state(proposal.id)
        assert state is not None
        text, _ = await proposal_view(services, state, None)
        edits.append((proposal.chat_id, proposal.message_id, text))
    for rename in await family.expire_overdue_renames():
        text, _ = await rename_view(services, rename, None)
        edits.append((rename.rename.chat_id, rename.rename.message_id, text))
    # Правки — после коммита: откат не должен оставить в чате «предложение сгорело».
    await services.session.commit()

    for chat_id, message_id, text in edits:
        if message_id is None:
            continue
        with quiet_edit("family expiry"):
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML"
            )
