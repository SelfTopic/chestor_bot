import logging
from typing import Any

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import Command, HasReplyUser, HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.game_configs import DUEL_CONFIG

from ....context import AppContext
from ....services.battle import DuelRefusal, DuelRefused
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import TextUserMessage, TextUserReplyMessage
from .keyboards import consent_keyboard

logger = logging.getLogger(__name__)


class DuelInvite:
    ctx: AppContext[Any]

    def refusal(self, refused: DuelRefused) -> Line:
        refusals = Dialogs.duel.refusals
        match refused.reason:
            case DuelRefusal.SELF:
                return refusals.self_duel()
            case DuelRefusal.NOT_REGISTERED:
                return refusals.not_registered()
            case DuelRefusal.INITIATOR_NO_PRIVATE_CHAT:
                return refusals.initiator_no_private_chat()
            case DuelRefusal.TARGET_NO_PRIVATE_CHAT:
                return refusals.target_no_private_chat()
            case DuelRefusal.INITIATOR_NO_GHOUL:
                return refusals.initiator_no_ghoul()
            case DuelRefusal.TARGET_NO_GHOUL:
                return refusals.target_no_ghoul()
            case DuelRefusal.DEAD:
                return refusals.dead()
            case DuelRefusal.NOT_COMBAT_READY:
                return refusals.not_combat_ready(
                    health=refused.health, threshold=refused.threshold
                )
            case DuelRefusal.BUSY:
                return refusals.busy()
            case DuelRefusal.PAIR_LIMIT:
                return refusals.pair_limit(
                    per_pair=DUEL_CONFIG.max_battles_per_day_pair
                )
            case DuelRefusal.INITIATOR_DAY_LIMIT:
                return refusals.initiator_day_limit(
                    per_day=DUEL_CONFIG.max_battles_per_day_total
                )
            case DuelRefusal.TARGET_DAY_LIMIT:
                return refusals.target_day_limit()
            case DuelRefusal.CLAIM_FAILED:
                return refusals.claim_failed()

    async def perform(self, telegram_id: int, args: Any) -> None:
        ctx = self.ctx
        message = ctx.message
        private = message.chat.type == "private"

        try:
            duel = await ctx.battle_service.open_duel(
                message.user.id, telegram_id, chat_id=message.chat.id, private=private
            )
        except DuelRefused as refused:
            await message.reply(ctx.text(self.refusal(refused)))
            return

        session = duel.session
        text = ctx.text(
            Dialogs.duel.invite(initiator=duel.initiator_name, target=duel.target_name)
        )
        keyboard = consent_keyboard(
            ctx.dialog_service,
            session.id,
            session.initiator_telegram_id,
            session.target_telegram_id,
        )

        if not private:
            sent = await message.answer(text, reply_markup=keyboard)
            await ctx.duel_service.atomic_update(
                session.id, "awaiting_consent", consent_message_id=sent.message_id
            )
            return

        for chat_id in (session.initiator_telegram_id, session.target_telegram_id):
            try:
                await ctx.bot.send_message(
                    chat_id=chat_id, text=text, reply_markup=keyboard
                )
            except TelegramAPIError:
                logger.warning(
                    "duel %s: failed to deliver invite to %s", session.id, chat_id
                )


class DuelRepliedArgs(CommandArgs):
    note: Rest = ""


class DuelRepliedHandler(
    DuelInvite,
    RepliedTargetHandler[DuelRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = Command("дуэль", DuelRepliedArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser() & HasReplyUser()


class DuelArgs(TargetArgs):
    target: Rest


class DuelHandler(
    DuelInvite,
    ExplicitTargetHandler[DuelArgs],
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = Command("дуэль", DuelArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser() & ~HasReplyUser()
    usage = Dialogs.duel.usage()
    reply_errors = True

    def not_found(self, target: str) -> Line:
        return Dialogs.duel.user_not_found(target=target)
