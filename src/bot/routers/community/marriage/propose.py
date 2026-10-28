from typing import Any

from selfrot import CommandArgs, InlineKeyboard, Rest
from selfrot.filter import AnyCommand, Command, HasMention, HasReplyUser, HasUser, TextRegexp
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from src.bot.dialogs import Dialogs, Line
from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.services.family import MarriageRefusal, MarriageRefused

from ....context import AppContext
from ...targeting import (
    ExplicitTargetHandler,
    RepliedTargetHandler,
    TargetArgs,
    is_bot_target,
)
from ...types import TextUserMessage, TextUserReplyMessage
from .payloads import ProposalPayment
from .render import PHRASES, mentions, proposal_view

TRIGGERS = ("брак", "свадьба", "marry", "wedding")


def refusal_line(reason: MarriageRefusal) -> Line:
    refusals = PHRASES.refusals
    match reason:
        case MarriageRefusal.SELF:
            return refusals.self()
        case MarriageRefusal.NOT_A_PERSON:
            return refusals.not_a_person()
        case MarriageRefusal.NOT_REGISTERED:
            return refusals.not_registered()
        case MarriageRefusal.SAME_FAMILY:
            return refusals.same_family()
        case MarriageRefusal.TARGET_MARRIED:
            return refusals.target_married()
        case MarriageRefusal.ALREADY_PROPOSED:
            return refusals.already_proposed()
        case MarriageRefusal.NOT_ENOUGH_MONEY:
            return refusals.not_enough_money(price=MARRIAGE_CONFIG.proposal_price)


class Proposal:
    ctx: AppContext[Any]

    async def perform(self, telegram_id: int, args: Any) -> None:
        ctx = self.ctx
        proposer_id = ctx.message.user.id
        if is_bot_target(ctx, telegram_id):
            await ctx.say(PHRASES.refusals.bot(), reply=True)
            return
        try:
            await ctx.family_service.check_proposal(proposer_id, telegram_id)
        except MarriageRefused as refused:
            await ctx.say(refusal_line(refused.reason), reply=True)
            return

        who = await mentions(ctx, (proposer_id, telegram_id))
        price = MARRIAGE_CONFIG.proposal_price
        ask = PHRASES.ask(proposer=who[proposer_id], target=who[telegram_id], price=price)
        pay = ProposalPayment(proposer_id=proposer_id, target_id=telegram_id)
        keyboard = InlineKeyboard().button(ctx.text(PHRASES.buttons.pay(price=price)), pay)
        # Не say(): кнопка потом правит это сообщение через edit_text.
        await ctx.message.reply(ctx.text(ask), reply_markup=keyboard.markup(), parse_mode="HTML")


class ProposalRepliedArgs(CommandArgs):
    pass


class ProposalRepliedHandler(
    Proposal,
    RepliedTargetHandler[ProposalRepliedArgs, AppContext[TextUserReplyMessage]],
):
    cmd = AnyCommand(
        *(
            Command(trigger, ProposalRepliedArgs, strict=True, prefixes="", ignore_case=True)
            for trigger in TRIGGERS
        )
    )
    query = cmd & HasUser() & HasReplyUser()


class ProposalArgs(TargetArgs):
    target: Rest


# Только с ником, id или кликабельным именем: иначе «брак — это скучно» в обычной
# переписке стало бы предложением.
EXPLICIT_TARGET = TextRegexp(r"(?i)(брак|свадьба|marry|wedding)\s+(@\w+|-?\d+)\s*$")


class ProposalHandler(Proposal, ExplicitTargetHandler[ProposalArgs, AppContext[TextUserMessage]]):
    cmd = AnyCommand(
        Command("брак", ProposalArgs, prefixes="", ignore_case=True),
        Command("свадьба", ProposalArgs, prefixes="", ignore_case=True),
        Command("marry", ProposalArgs, prefixes="", ignore_case=True),
        Command("wedding", ProposalArgs, prefixes="", ignore_case=True),
    )
    query = cmd & HasUser() & ~HasReplyUser() & (EXPLICIT_TARGET | HasMention())
    reply_errors = True

    def not_found(self, target: str) -> Line:
        return PHRASES.user_not_found(target=target)


class ProposalPaymentHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = ProposalPayment.filter().pressed_by("proposer_id")
    query = press

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        payload = self.press.parse(ctx)
        message = callback.message
        if not isinstance(message, Message):
            await callback.answer(ctx.text(Dialogs.errors.cannot_process()))
            return

        try:
            state = await ctx.family_service.propose(
                payload.proposer_id, payload.target_id, chat_id=message.chat.id
            )
        except MarriageRefused as refused:
            await callback.answer(ctx.text(refusal_line(refused.reason)), show_alert=True)
            return

        text, keyboard = await proposal_view(ctx, state, ctx.bot)
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await ctx.family_service.set_message(state.proposal.id, message.message_id)
        await callback.answer()
