import html
from datetime import datetime

from selfrot import InlineKeyboard, MessageHandler
from selfrot.filter import HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from src.bot.dialogs import Dialogs, LineText
from src.bot.services.family import NotMarried
from src.bot.dialogs.vocab import time_text
from src.bot.utils import age_parts, format_amount, utcnow_naive

from ....context import AppContext
from ...types import TextUserMessage
from .payloads import DivorcePress
from .render import mentions


def age(text: LineText, since: datetime) -> str:
    return time_text(text, age_parts(int((utcnow_naive() - since).total_seconds())))


class FamilyHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (Text("семья", ignore_case=True) | Text("family", ignore_case=True)) & HasUser()

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
                    name=who[member.telegram_id],
                    since=member.joined_at.strftime("%d.%m.%Y"),
                    age=age(ctx.text, member.joined_at),
                )
            )
            for member in family.members
        )
        title = (
            Dialogs.family.title_named(name=html.escape(family.name))
            if family.name
            else Dialogs.family.title()
        )
        view = Dialogs.family.view(title=title, balance=format_amount(family.balance), rows=rows)
        await ctx.say(view, reply=True, parse_mode="HTML")


# Сообщение Telegram ограничено 4096 символами: дальше «и ещё N».
LIST_LIMIT = 3500


class FamiliesHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (Text("браки", ignore_case=True) | Text("families", ignore_case=True)) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        families = await ctx.family_service.families_in_chat(ctx.message.chat.id)
        if not families:
            await ctx.say(Dialogs.family.list.empty(), reply=True)
            return

        rows: list[str] = []
        for place, family in enumerate(families, start=1):
            members = ", ".join(family.member_names)
            since = family.created_at.strftime("%d.%m.%Y")
            line = (
                Dialogs.family.list.named_row(
                    place=place,
                    name=family.name,
                    members=members,
                    since=since,
                    age=age(ctx.text, family.created_at),
                )
                if family.name
                else Dialogs.family.list.row(
                    place=place, members=members, since=since, age=age(ctx.text, family.created_at)
                )
            )
            row = ctx.text(line)
            if sum(len(r) + 1 for r in rows) + len(row) > LIST_LIMIT:
                rows.append(ctx.text(Dialogs.family.list.more(count=len(families) - len(rows))))
                break
            rows.append(row)
        listing = Dialogs.family.list.message(count=len(families), rows="\n".join(rows))
        await ctx.say(listing, reply=True)


class DivorceHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (Text("развод", ignore_case=True) | Text("divorce", ignore_case=True)) & HasUser()

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
