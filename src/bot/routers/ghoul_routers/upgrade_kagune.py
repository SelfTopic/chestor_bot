import logging
import time
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import (
    CooldownService,
    DialogService,
    GhoulService,
    MediaService,
    UserService,
)
from ...types import KaguneType
from ...utils import calculate_kagune, parse_seconds

router = Router(name=__name__)
logger = logging.getLogger(__name__)

_CALLBACK_PREFIX = "kagune_upgrade_"


def parse_kagune_callback_payload(payload: str) -> Optional[tuple[int, str]]:
    """Разбирает "<invoker_id>_<name_english>" -> (invoker_id, name_english),
    или None, если формат не тот. Вынесено в чистую функцию специально ради
    юнит-теста - это единственное, что защищает клавиатуру от нажатия чужим
    человеком в группе (см. авторизацию в upgrade_kagune_callback)."""

    try:
        invoker_id_str, name_english = payload.rsplit("_", 1)
    except ValueError:
        return None

    if not invoker_id_str.isdigit():
        return None

    return int(invoker_id_str), name_english


async def _do_upgrade(
    telegram_id: int,
    first_name: str,
    kagune_type: KaguneType,
    ghoul_service: GhoulService,
    dialog_service: DialogService,
    user_service: UserService,
    cooldown_service: CooldownService,
) -> tuple[bool, str]:
    """Проверки + сама прокачка. Возвращает (успех, текст) - текст либо
    причина отказа, либо готовое сообщение об успехе. Переиспользуется и
    прямым (один тип кагуне) и колбэк (несколько типов) путём - между
    показом клавиатуры и нажатием могло пройти время, поэтому кулдаун и
    баланс перепроверяются здесь заново, а не только один раз в хендлере."""

    ghoul = await ghoul_service.get(telegram_id)
    if not ghoul:
        return False, "Гуль не найден."

    current_strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
    if current_strength is None:
        return False, "Этот тип кагуне у тебя не открыт."

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=telegram_id, cooldown_name="KAGUNE_UPGRADE"
    )
    if user_cooldown:
        cooldown_parsed = parse_seconds(
            total_seconds=int(user_cooldown.end_at - time.time())
        )
        return False, dialog_service.text(
            key="upgrade_kagune_cooldown_error",
            minutes=str(cooldown_parsed.minutes_remaining),
            seconds=str(cooldown_parsed.seconds_remaining),
        )

    price_upgrade = ghoul_service.calculate_price_upgrade_kagune(current_strength)
    user = await user_service.get(find_by=telegram_id)
    if not user:
        return False, "Пользователь не найден."

    if user.balance < price_upgrade:
        return False, dialog_service.text(
            key="not_enough_money", money=int(price_upgrade - user.balance) + 1
        )

    await user_service.minus_balance(
        telegram_id=telegram_id, change_balance=price_upgrade, log="upgrade kagune"
    )
    new_ghoul = await ghoul_service.upgrade_kagune(
        telegram_id=telegram_id, kagune_type=kagune_type
    )
    await cooldown_service.set_cooldown(
        telegram_id=telegram_id, cooldown_type="KAGUNE_UPGRADE"
    )

    new_strength = ghoul_service.get_kagune_strength(new_ghoul, kagune_type)
    text = dialog_service.text(
        key="upgrade_kagune_accept",
        name=first_name,
        kagune_strength=str(new_strength),
        money=str(price_upgrade),
    )
    return True, text


async def _send_result(
    message: Message,
    media_service: MediaService,
    telegram_id: int,
    kagune_type: KaguneType,
    text: str,
) -> None:
    media = await media_service.get_random_gif(
        f"kagune {kagune_type.value['name_english']}", user_id=telegram_id
    )

    if not media:
        await message.answer(text=text)
        return

    logger.debug(f"Media path: {media.path}, media file_id: {media.telegram_file_id}")

    try:
        await message.answer_animation(
            animation=media.telegram_file_id or FSInputFile(media.path), caption=text
        )
    except TelegramBadRequest:
        animation = FSInputFile(media.path)
        my_message = await message.answer_animation(animation=animation, caption=text)

        if not my_message.animation:
            raise

        await media_service.update_telegram_file_id(
            path=media.path, new_file_id=my_message.animation.file_id
        )


def _build_choice_keyboard(
    ghoul_service: GhoulService, ghoul, owned: list[KaguneType], invoker_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """invoker_id зашивается прямо в callback_data - в группе клавиатуру
    видят все, а нажать имеет право только тот, кто вызвал команду (иначе
    любой тролль перехватывает чужой выбор себе, см. обработчик колбэка)."""

    lines = ["Какое кагуне усилить?"]
    rows = []

    for kagune_type in owned:
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        price = ghoul_service.calculate_price_upgrade_kagune(strength or 0)
        lines.append(f"{kagune_type.value['name']} (сила {strength}) - {price} CheSton")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{kagune_type.value['name']} - {price} CheSton",
                    callback_data=(
                        f"{_CALLBACK_PREFIX}{invoker_id}_{kagune_type.value['name_english']}"
                    ),
                )
            ]
        )

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text.lower() == "растить кагуне")
@inject
async def upgrade_kagune(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    user_service: UserService = Provide[Container.user_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    media_service: MediaService = Provide[Container.media_service],
):
    if not message.from_user:
        raise ValueError("User from message not found")

    ghoul = await ghoul_service.get(message)

    if not ghoul:
        new_ghoul = await ghoul_service.register(message.from_user.id)

        if not new_ghoul.ghoul:
            raise ValueError("Ghoul is not found")

        return await message.reply(
            text=dialog_service.text(
                key="new_ghoul",
                name=message.from_user.first_name,
                kagune_type=calculate_kagune(new_ghoul.ghoul.kagune_type_bit)[0].value[
                    "name"
                ],
            )
        )

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=message.from_user.id, cooldown_name="KAGUNE_UPGRADE"
    )

    if user_cooldown:
        cooldown_parsed = parse_seconds(
            total_seconds=int(user_cooldown.end_at - time.time())
        )

        return await message.reply(
            text=dialog_service.text(
                key="upgrade_kagune_cooldown_error",
                minutes=str(cooldown_parsed.minutes_remaining),
                seconds=str(cooldown_parsed.seconds_remaining),
            )
        )

    owned = ghoul_service.owned_kagune_types(ghoul)

    if not owned:
        raise ValueError("Ghoul has no kagune type")

    if len(owned) > 1:
        text, keyboard = _build_choice_keyboard(
            ghoul_service, ghoul, owned, invoker_id=message.from_user.id
        )
        await message.reply(text=text, reply_markup=keyboard)
        return

    ok, text = await _do_upgrade(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name or "Ghoul",
        kagune_type=owned[0],
        ghoul_service=ghoul_service,
        dialog_service=dialog_service,
        user_service=user_service,
        cooldown_service=cooldown_service,
    )

    if not ok:
        await message.reply(text=text)
        return

    await _send_result(message, media_service, message.from_user.id, owned[0], text)


@router.callback_query(lambda c: c.data and c.data.startswith(_CALLBACK_PREFIX))
@inject
async def upgrade_kagune_callback(
    callback_query: CallbackQuery,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    user_service: UserService = Provide[Container.user_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    media_service: MediaService = Provide[Container.media_service],
) -> None:
    if not callback_query.data or not callback_query.from_user:
        await callback_query.answer("Невозможно обработать запрос")
        return

    if not isinstance(callback_query.message, Message):
        await callback_query.answer("Невозможно обработать запрос")
        return

    payload = callback_query.data[len(_CALLBACK_PREFIX) :]
    parsed = parse_kagune_callback_payload(payload)

    if parsed is None:
        await callback_query.answer("Неверные данные кнопки")
        return

    invoker_id, name_english = parsed

    if invoker_id != callback_query.from_user.id:
        # Клавиатуру видят все в чате, но нажать имеет право только тот, кто
        # вызвал "растить кагуне" - без edit_reply_markup, чтобы настоящий
        # вызывающий мог нажать позже как ни в чём не бывало.
        await callback_query.answer("Это не твоя кнопка", show_alert=True)
        return

    kagune_type = next(
        (kt for kt in KaguneType if kt.value["name_english"] == name_english), None
    )

    if kagune_type is None:
        await callback_query.answer("Неверный тип кагуне")
        return

    telegram_id = callback_query.from_user.id

    ok, text = await _do_upgrade(
        telegram_id=telegram_id,
        first_name=callback_query.from_user.first_name or "Ghoul",
        kagune_type=kagune_type,
        ghoul_service=ghoul_service,
        dialog_service=dialog_service,
        user_service=user_service,
        cooldown_service=cooldown_service,
    )

    if not ok:
        await callback_query.answer(text, show_alert=True)
        return

    await callback_query.answer()
    await callback_query.message.delete()
    await _send_result(
        callback_query.message, media_service, telegram_id, kagune_type, text
    )


__all__ = ["router"]
