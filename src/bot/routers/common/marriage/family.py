from selfrot import InlineKeyboard, MessageHandler
from selfrot.filter import HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from src.bot.dialogs import Dialogs
from src.bot.services.family import NotMarried

from ....context import AppContext
from ...types import TextUserMessage
from .payloads import DivorcePress
from .render import mentions


class FamilyHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("семья", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        family = await ctx.family_service.family(ctx.message.user.id)
        if family is None:
            await ctx.say(Dialogs.family.single(), reply=True)
            return

        who = await mentions(ctx, tuple(member.telegram_id for member in family.members))
        rows = "\n".join(
            ctx.text(
                Dialogs.family.row(
                    name=who[member.telegram_id], since=member.joined_at.strftime("%d.%m.%Y")
                )
            )
            for member in family.members
        )
        view = Dialogs.family.view(balance=family.balance, rows=rows)
        await ctx.say(view, reply=True, parse_mode="HTML")


class DivorceHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("развод", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        user_id = ctx.message.user.id
        if await ctx.family_service.family(user_id) is None:
            await ctx.say(Dialogs.divorce.not_married(), reply=True)
            return

        press = DivorcePress(expected_id=user_id)
        keyboard = InlineKeyboard().button(ctx.text(Dialogs.divorce.button()), press)
        # Не say(): кнопка потом правит это сообщение через edit_text.
        await ctx.message.reply(ctx.text(Dialogs.divorce.ask()), reply_markup=keyboard.markup())


class DivorcePressHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = DivorcePress.filter().pressed_by("expected_id")
    query = press

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        user_id = self.press.parse(ctx).expected_id
        try:
            divorce = await ctx.family_service.divorce(user_id)
        except NotMarried:
            await callback.answer(ctx.text(Dialogs.divorce.stale()), show_alert=True)
            return

        heir = divorce.heir
        who = await mentions(ctx, (user_id,) if heir is None else (user_id, heir))
        line = (
            Dialogs.divorce.done(name=who[user_id])
            if heir is None
            else Dialogs.divorce.dissolved(
                name=who[user_id], heir=who[heir], amount=divorce.inherited
            )
        )
        message = callback.message
        if isinstance(message, Message):
            await message.edit_text(ctx.text(line), parse_mode="HTML")
        await callback.answer()
