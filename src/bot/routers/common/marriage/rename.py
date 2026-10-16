import logging

from selfrot import CommandArgs, InlineKeyboard, MessageHandler, Rest, button
from selfrot.filter import Command, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from src.bot.dialogs import Line
from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.services.family import ConsentRefused, RenameRefusal, RenameRefused, RenameState

from ....context import AppContext
from ...types import TextUserMessage, UserMessage
from ...utils import quiet_edit
from .consent import refusal_line
from .payloads import FamilyRenameAnswer, RenameLink
from .render import RENAME, rename_view

logger = logging.getLogger(__name__)


def refusal(reason: RenameRefusal) -> Line:
    match reason:
        case RenameRefusal.NOT_MARRIED:
            return RENAME.refusals.not_married()
        case RenameRefusal.BAD_NAME:
            return RENAME.refusals.bad_name(limit=MARRIAGE_CONFIG.family_name_max_length)
        case RenameRefusal.ALREADY_PENDING:
            return RENAME.refusals.already_pending()


class RenameArgs(CommandArgs):
    name: Rest = ""


class RenameHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = Command("имя семьи", RenameArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        name = self.cmd.parse(ctx).name
        if not name.strip():
            await ctx.say(RENAME.usage(), reply=True)
            return
        try:
            state = await ctx.family_service.propose_rename(
                ctx.message.user.id, name, chat_id=ctx.message.chat.id
            )
        except RenameRefused as refused:
            await ctx.say(refusal(refused.reason), reply=True)
            return

        text, keyboard = await rename_view(ctx, state, ctx.bot)
        # Не say(): кнопки потом правят это сообщение через edit_text.
        sent = await ctx.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
        await ctx.family_service.set_rename_message(state.rename.id, sent.message_id)


class RenameAnswerHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    agreed = FamilyRenameAnswer.filter(answer="agree")
    declined = FamilyRenameAnswer.filter(answer="decline")

    @agreed
    async def agree(self) -> None:
        state = await self.answer(self.agreed.parse(self.ctx).rename_id, agree=True)
        if state is not None:
            done = RENAME.consent.renamed() if state.renamed else RENAME.consent.accepted()
            await self.show(state, RENAME.voted(), done)

    @declined
    async def decline(self) -> None:
        state = await self.answer(self.declined.parse(self.ctx).rename_id, agree=False)
        if state is not None:
            await self.show(state, RENAME.declined_private(), RENAME.consent.declined())

    async def answer(self, rename_id: int, agree: bool) -> RenameState | None:
        callback = self.ctx.callback_query
        try:
            return await self.ctx.family_service.answer_rename(
                rename_id, callback.user.id, agree=agree
            )
        except ConsentRefused as refused:
            await callback.answer(self.ctx.text(refusal_line(refused.reason)), show_alert=True)
            return None

    async def show(self, state: RenameState, private_line: Line, alert: Line) -> None:
        rename = state.rename
        callback = self.ctx.callback_query
        if rename.message_id is not None:
            text, keyboard = await rename_view(self.ctx, state, self.ctx.bot)
            with quiet_edit("family rename"):
                await self.ctx.bot.edit_message_text(
                    chat_id=rename.chat_id,
                    message_id=rename.message_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
        message = callback.message
        # Ответ из лички: там правится своё сообщение, а предложение — в чате.
        if isinstance(message, Message) and message.message_id != rename.message_id:
            with quiet_edit("family rename private answer"):
                await message.edit_text(self.ctx.text(private_line))
        await callback.answer(self.ctx.text(alert))


class RenameLinkHandler(MessageHandler[AppContext[UserMessage]]):
    link = Command("start", RenameLink, deep_link=True)
    query = link & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        state = await ctx.family_service.rename_state(self.link.parse(ctx).rename_id)
        if state is None or state.rename.stage != "awaiting":
            await ctx.say(RENAME.link_stale())
            return
        if ctx.message.user.id not in state.members:
            await ctx.say(RENAME.link_not_family())
            return

        rename_id = state.rename.id
        keyboard = InlineKeyboard().row(
            button(
                ctx.text(RENAME.buttons.agree()),
                FamilyRenameAnswer(rename_id=rename_id, answer="agree"),
            ),
            button(
                ctx.text(RENAME.buttons.decline()),
                FamilyRenameAnswer(rename_id=rename_id, answer="decline"),
            ),
        )
        vote = RENAME.vote(name=state.rename.name)
        await ctx.message.answer(ctx.text(vote), reply_markup=keyboard.markup())
