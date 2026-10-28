from typing import Any

from selfrot import BaseRouter, CallbackPayload, InlineKeyboard, MessageHandler, button
from selfrot.filter import Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Chat, InlineKeyboardMarkup, Message

from src.bot.dialogs import Dialogs, Line

from ...context import AppContext
from ..types import DataMessageCallbackQuery, UserMessage

# Каждый язык подписан на самом себе: иранец узнает «فارسی», даже если бот говорит по-английски.
LANGUAGE_NAMES: dict[str, Line] = {
    "ru": Dialogs.language.name.ru(),
    "en": Dialogs.language.name.en(),
}
GROUP_CHATS = ("group", "supergroup")


class LanguagePress(CallbackPayload, prefix="lang"):
    language: str


def is_group(chat: Chat) -> bool:
    return chat.type in GROUP_CHATS


async def is_admin(ctx: AppContext[Any], telegram_id: int) -> bool:
    administrators = await ctx.chat_administrators()
    return any(admin.user.id == telegram_id for admin in administrators)


def keyboard(ctx: AppContext[Any]) -> InlineKeyboardMarkup:
    buttons = InlineKeyboard()
    for language in ctx.dialog_service.languages():
        name = LANGUAGE_NAMES.get(language)
        if name is not None:
            buttons.row(button(ctx.text(name), LanguagePress(language=language)))
    return buttons.markup()


class LanguageHandler(MessageHandler[AppContext[UserMessage]]):
    query = Command("lang") & HasUser()

    async def handle(self) -> None:
        message = self.ctx.message
        if is_group(message.chat) and not await is_admin(self.ctx, message.user.id):
            await self.ctx.say(Dialogs.language.admins_only(), reply=True)
            return
        await message.reply(
            self.ctx.text(Dialogs.language.choose()), reply_markup=keyboard(self.ctx)
        )


class LanguagePressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = LanguagePress.filter()
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        message = callback.message
        language = self.press.parse(self.ctx).language
        name = LANGUAGE_NAMES.get(language)
        if not isinstance(message, Message) or name is None:
            await callback.answer(self.ctx.text(Dialogs.errors.cannot_process()))
            return

        languages = self.ctx.language_service
        if is_group(message.chat):
            if not await is_admin(self.ctx, callback.user.id):
                await callback.answer(
                    self.ctx.text(Dialogs.language.admins_only()), show_alert=True
                )
                return
            await languages.choose_for_chat(message.chat.id, message.chat.title, language)
            done = Dialogs.language.chat_set(language=name)
        else:
            await languages.choose_for_user(callback.user.id, language)
            done = Dialogs.language.private_set(language=name)

        await message.edit_text(self.ctx.dialog_service.text(done, language))
        await callback.answer()


class LanguageRouter(BaseRouter[AppContext]):
    handlers = (LanguageHandler, LanguagePressHandler)
