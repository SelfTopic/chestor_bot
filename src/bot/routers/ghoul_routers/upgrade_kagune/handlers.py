"""
"растить кагуне": регистрация/возрождение отделены от прокачки — NeedsRegistrationOrRebirth
(filters.py) решает, какой из хендлеров сработает, чтобы логика прокачки не была
захламлена веткой "гуля ещё нет"/"гуль мёртв". Ровно поэтому в UpgradeKaguneHandler
можно использовать ctx.db_ghoul(): фильтр уже гарантировал, что гуль есть и жив.
"""

import time
from typing import Any

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasMessageCallbackQuery, HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.types import KaguneType, MediaDownloadType
from src.bot.utils import calculate_kagune, parse_seconds

from ....context import AppContext
from ....services.media_paths import random_media
from ...types import DataMessageCallbackQuery, TextUserMessage
from .callback_data import KaguneUpgradePress
from .filters import NeedsRegistrationOrRebirth
from .upgrade import build_choice_keyboard, do_upgrade

_COMMAND = Text("растить кагуне", ignore_case=True) & HasUser()


async def _send_upgrade_result(
    ctx: AppContext[Any], telegram_id: int, kagune_type: KaguneType, text: str
) -> None:
    media = await random_media(
        ctx.media_repository,
        MediaDownloadType.ANIMATION,
        f"kagune {kagune_type.value['name_english']}",
        telegram_id,
    )
    if media is None:
        await ctx.answer_message(text)
        return

    await ctx.answer_gif(media, caption=text)


class RegisterOrRebirthHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = _COMMAND & NeedsRegistrationOrRebirth()

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        telegram_id = message.user.id

        ghoul = await ctx.ghoul_service.get(find_by=telegram_id)

        if ghoul is None:
            new_ghoul = await ctx.ghoul_service.register(telegram_id)
            if new_ghoul.ghoul is None:
                raise ValueError("Ghoul is not found")

            kagune_type = calculate_kagune(new_ghoul.ghoul.kagune_type_bit)[0]
            await message.reply(
                text=ctx.dialog_service.text(
                    key="new_ghoul",
                    name=message.user.first_name,
                    kagune_type=kagune_type.value["name"],
                )
            )
            return

        reborn = await ctx.ghoul_service.reset_for_rebirth(telegram_id)
        new_type = calculate_kagune(reborn.kagune_type_bit)[0]
        await message.reply(
            text=ctx.dialog_service.text(
                key="rebirth_accept", kagune_type=new_type.value["name"]
            )
        )


class UpgradeKaguneHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = _COMMAND & ~NeedsRegistrationOrRebirth()

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        telegram_id = message.user.id
        first_name = message.user.first_name

        ghoul = await ctx.db_ghoul()

        cooldown = await ctx.cooldown_service.get_active_cooldown(
            telegram_id, "KAGUNE_UPGRADE"
        )
        if cooldown is not None:
            remaining = parse_seconds(int(cooldown.end_at - time.time()))
            await message.reply(
                text=ctx.dialog_service.text(
                    key="upgrade_kagune_cooldown_error",
                    minutes=str(remaining.minutes_remaining),
                    seconds=str(remaining.seconds_remaining),
                )
            )
            return

        owned = ctx.ghoul_service.owned_kagune_types(ghoul)
        if not owned:
            raise ValueError("Ghoul has no kagune type")

        if len(owned) > 1:
            text, keyboard = build_choice_keyboard(ctx, ghoul, owned, telegram_id)
            await message.reply(text=text, reply_markup=keyboard)
            return

        ok, text = await do_upgrade(ctx, telegram_id, first_name, owned[0])
        if not ok:
            await message.reply(text=text)
            return

        await _send_upgrade_result(ctx, telegram_id, owned[0], text)


class KaguneChoiceHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    """Клавиатуру в группе видят все, а нажать имеет право только тот, кто вызвал
    "растить кагуне" — pressed_by("invoker_id") делает так, что query не совпадает
    для чужого нажатия: оно просто ни на что не отвечает."""

    press = KaguneUpgradePress.filter().pressed_by("invoker_id")
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        message = callback.message

        if not isinstance(message, Message):
            return

        payload = self.press.parse(ctx)
        kagune_type = next(
            (
                kt
                for kt in KaguneType
                if kt.value["name_english"] == payload.name_english
            ),
            None,
        )
        if kagune_type is None:
            await callback.answer("Неверный тип кагуне")
            return

        telegram_id = callback.user.id
        first_name = callback.user.first_name

        ok, text = await do_upgrade(ctx, telegram_id, first_name, kagune_type)
        if not ok:
            await callback.answer(text, show_alert=True)
            return

        await callback.answer()
        await message.delete()
        await _send_upgrade_result(ctx, telegram_id, kagune_type, text)


class UpgradeKaguneRouter(BaseRouter[AppContext]):
    handlers = (
        RegisterOrRebirthHandler,
        UpgradeKaguneHandler,
        KaguneChoiceHandler,
    )
