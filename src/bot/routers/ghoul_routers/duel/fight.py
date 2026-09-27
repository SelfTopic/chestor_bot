import logging

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError

from src.bot.dialogs import Dialogs
from src.bot.services.dialog import DialogService
from src.database.models import DuelSession

from ....repositories.fight import Score
from ....services.battle import DuelOutcome
from ..battle_text import BattleMessage
from .keyboards import outcome_keyboard
from .services import DuelServices

logger = logging.getLogger(__name__)


async def run_and_announce_fight(
    bot: Bot, duel: DuelSession, services: DuelServices
) -> DuelSession | None:
    fight = await services.battle.fight_duel(duel)
    if fight is None:
        return None

    message = BattleMessage(services.battle_text_generator, fight.report)
    keyboard = (
        outcome_keyboard(services.dialogs, duel.id, fight.winner_telegram_id)
        if fight.winner_telegram_id
        else None
    )

    async def announce(chat_id: int) -> int | None:
        sent = await message.send(bot, chat_id, keyboard)
        if sent is None:
            logger.warning("duel %s: failed to announce fight result to %s", duel.id, chat_id)
            return None
        return sent.message_id

    outcome_message_id = None
    if duel.is_private_origin:
        await announce(duel.initiator_telegram_id)
        await announce(duel.target_telegram_id)
    else:
        outcome_message_id = await announce(duel.chat_id)

    return await services.battle.finish_duel_fight(duel, fight, outcome_message_id)


async def finalize_outcome(
    bot: Bot, duel: DuelSession, action: str, services: DuelServices
) -> None:
    outcome = await services.battle.resolve_duel_outcome(duel, action)

    if duel.outcome_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=duel.chat_id, message_id=duel.outcome_message_id, reply_markup=None
            )
        except TelegramAPIError:
            pass

    chat_ids = {duel.initiator_telegram_id, duel.target_telegram_id}
    if not duel.is_private_origin:
        chat_ids.add(duel.chat_id)

    text = outcome_text(services.dialogs, outcome)
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except TelegramAPIError:
            pass


def outcome_text(dialogs: DialogService, outcome: DuelOutcome) -> str:
    phrases = Dialogs.duel.outcome
    winner, loser = outcome.winner_name, outcome.loser_name

    if outcome.action == "outcome_rob":
        line = (
            phrases.robbed(winner=winner, loser=loser, amount=outcome.reward_balance)
            if outcome.reward_balance
            else phrases.robbed_nothing(winner=winner, loser=loser)
        )
    elif outcome.action == "outcome_eat":
        line = (
            phrases.eaten(winner=winner, loser=loser, rc=outcome.reward_rc)
            if outcome.reward_rc
            else phrases.eaten_nothing(winner=winner, loser=loser)
        )
    else:
        line = phrases.released(winner=winner, loser=loser)
    text = dialogs.text(line)

    if outcome.action == "outcome_eat" and outcome.hunger_restored is not None:
        restored = phrases.hunger(winner=winner, restored=outcome.hunger_restored)
        text += "\n" + dialogs.text(restored)

    if outcome.reward_level_progress is not None:
        progress = f"{outcome.reward_level_progress:.2f}"
        experience = phrases.experience(winner=winner, progress=progress)
        text += "\n\n" + dialogs.text(experience)

    text += "\n\n" + _score_line(dialogs, winner, outcome.winner_score)
    text += "\n" + _score_line(dialogs, loser, outcome.loser_score)
    return text


def _score_line(dialogs: DialogService, name: str, score: Score) -> str:
    return dialogs.text(
        Dialogs.duel.outcome.score(
            name=name, total=score.total, wins=score.wins, losses=score.losses
        )
    )
