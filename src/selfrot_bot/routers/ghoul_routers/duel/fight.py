"""
Дуэль на стороне Telegram: объявить бой и объявить исход. Всё, что считается и
пишется в БД, делает BattleService (services/battle.py); здесь только что и в
какие чаты отправить. Общее для нажатий (callbacks.py) и таймаутов (ticker.py),
поэтому получает только Bot и DuelServices.

Как у прода, у дуэли из лички (is_private_origin) бой и исход дублируются в оба
личных чата, а id сообщения с кнопками исхода не запоминается: там клавиатуру
после выбора не убираем.
"""

import logging

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError

from src.database.models import DuelSession

from ....repositories.battle import Score
from ....services.battle import DuelOutcome
from ..battle_text import BattleMessage
from .keyboards import outcome_keyboard
from .services import DuelServices

logger = logging.getLogger(__name__)


async def run_and_announce_fight(
    bot: Bot, duel: DuelSession, services: DuelServices
) -> DuelSession | None:
    """Состояние дуэли после боя; None — участник исчез, дуэль закрыта. Стадия
    "awaiting_winner_choice" значит, что ждём выбор победителя (таймаут — DuelTicker)."""
    fight = await services.battle.fight_duel(duel)
    if fight is None:
        return None

    message = BattleMessage(services.battle_text_generator, fight.report)
    keyboard = (
        outcome_keyboard(duel.id, fight.winner_telegram_id)
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
    """Исход "ограбить/отпустить/съесть". Вызывать только после того, как
    atomic_update реально перевёл дуэль в "done" с этим выбором."""
    outcome = await services.battle.resolve_duel_outcome(duel, action)

    if duel.outcome_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=duel.chat_id, message_id=duel.outcome_message_id, reply_markup=None
            )
        except TelegramAPIError:
            pass

    # Итог всегда дублируется в личку обоим, чтобы бой можно было найти в
    # переписке; у дуэли из лички это и есть единственная доставка.
    chat_ids = {duel.initiator_telegram_id, duel.target_telegram_id}
    if not duel.is_private_origin:
        chat_ids.add(duel.chat_id)

    text = outcome_text(outcome)
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except TelegramAPIError:
            pass


def outcome_text(outcome: DuelOutcome) -> str:
    winner, loser = outcome.winner_name, outcome.loser_name

    # Опечатки ("у тот", "у нечего") как у прода.
    if outcome.action == "outcome_rob":
        text = (
            f"💰 {winner} ограбил {loser} и забрал {outcome.reward_balance} CheSton's!"
            if outcome.reward_balance
            else f"💰 {winner} попытался ограбить {loser}, но у тот оказался "
            "ебаный бомж и у нечего взять."
        )
    elif outcome.action == "outcome_eat":
        text = (
            f"🍖 {winner} нещадно добил и сожрал {loser}, "
            f"получив {outcome.reward_rc} RC-клеток"
            if outcome.reward_rc
            else f"🍖 {winner} нещадно добил и сожрал {loser}, но в его "
            "теле не оказалось пригодных для переваривания RC клеток"
        )
        if outcome.hunger_restored is not None:
            text += f"\n🍖 Голод {winner} восстановлен на {outcome.hunger_restored}%."
    else:
        text = f"🕊️ {winner} решил отпустить {loser}."

    if outcome.reward_level_progress is not None:
        text += (
            f"\n\n📈 {winner} получил "
            f"{outcome.reward_level_progress:.2f}% опыта за победу."
        )

    # Счёт только дуэлей (BATTLE_ENGINE.md 5.2), уже с этим боем.
    text += "\n\n" + _score_line(winner, outcome.winner_score)
    text += "\n" + _score_line(loser, outcome.loser_score)
    return text


def _score_line(name: str, score: Score) -> str:
    return f"📊 {name}: {score.total} боёв ({score.wins}П/{score.losses})"
