import html

from selfrot import InlineKeyboard, button
from selfrot.types import InlineKeyboardMarkup

from src.bot.dialogs import Dialogs, Line
from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.services.family import MarriageFailure, ProposalState
from src.bot.session_services import SessionServices

from .payloads import MarriageAnswer

PHRASES = Dialogs.marriage
LINK_PREFIX = "marry_"


def mention(telegram_id: int, name: str) -> str:
    return f'<a href="tg://user?id={telegram_id}">{html.escape(name)}</a>'


async def mentions(services: SessionServices, telegram_ids: tuple[int, ...]) -> dict[int, str]:
    names = await services.first_names(telegram_ids)
    return {tid: mention(tid, names.get(tid, str(tid))) for tid in telegram_ids}


def failure_line(state: ProposalState, who: dict[int, str]) -> Line:
    proposer, target = (who[tid] for tid in state.required[:2])
    match state.failure:
        case MarriageFailure.TARGET_TAKEN:
            return PHRASES.failed.target_taken(target=target)
        case MarriageFailure.FAMILY_CHANGED:
            return PHRASES.failed.family_changed(proposer=proposer)
        case _:
            return PHRASES.failed.target_broke(
                target=target, price=MARRIAGE_CONFIG.acceptance_price
            )


async def proposal_view(
    services: SessionServices, state: ProposalState, bot_username: str | None
) -> tuple[str, InlineKeyboardMarkup | None]:
    text = services.dialog_service.text
    who = await mentions(services, state.required)
    proposer, target = state.required[:2]

    if state.married:
        members = ", ".join(who[tid] for tid in state.required)
        return text(PHRASES.married(target=who[target], members=members)), None
    if state.failure is not None:
        return text(failure_line(state, who)), None
    declined_by = state.proposal.declined_by
    if declined_by is not None:
        line = PHRASES.declined(
            name=who[declined_by], proposer=who[proposer], price=MARRIAGE_CONFIG.proposal_price
        )
        return text(line), None
    if state.proposal.stage == "expired":
        line = PHRASES.expired(proposer=who[proposer], price=MARRIAGE_CONFIG.proposal_price)
        return text(line), None

    rows = "\n".join(
        text(PHRASES.row_confirmed(name=who[tid]))
        if tid in state.consented
        else text(PHRASES.row_waiting(name=who[tid]))
        for tid in state.required
    )
    body = text(PHRASES.invite(proposer=who[proposer], target=who[target], rows=rows))

    keyboard = InlineKeyboard()
    proposal_id = state.proposal.id
    if proposer not in state.consented:
        press = MarriageAnswer(proposal_id=proposal_id, expected_id=proposer, answer="agree")
        keyboard.row(button(text(PHRASES.buttons.proposer()), press))
    decline = MarriageAnswer(proposal_id=proposal_id, expected_id=target, answer="decline")
    target_row = [button(text(PHRASES.buttons.decline()), decline)]
    if target not in state.consented:
        press = MarriageAnswer(proposal_id=proposal_id, expected_id=target, answer="agree")
        target_row.insert(0, button(text(PHRASES.buttons.target()), press))
    keyboard.row(*target_row)
    if state.family_members:
        body += "\n\n" + text(PHRASES.family_hint(proposer=who[proposer]))
        if bot_username:
            link = f"https://t.me/{bot_username}?start={LINK_PREFIX}{proposal_id}"
            keyboard.row(button(text(PHRASES.buttons.family()), url=link))
    return body, keyboard.markup()
