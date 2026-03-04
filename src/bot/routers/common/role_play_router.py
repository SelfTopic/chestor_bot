from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.exceptions import RpCommandValidateError, UserNotFound
from src.bot.filters import RpCommandFilter
from src.bot.services import RpCommandsService, UserService
from src.bot.types.rp_commands import RpCommandDTO, TypeRpCommandEnum

router = Router(name=__name__)


@router.message(Command("set_rp"))
@inject
async def new_rp_handler(
    message: Message,
    command: CommandObject,
    rp_commands_service: RpCommandsService = Provide[Container.rp_commands_service],
) -> None:
    args = command.args

    if not args or len(args.split()) < 2:
        raise RpCommandValidateError(
            "Используйте как /set_rp\n<команда>\n<действие>\nнапример:\n/set_rp\nпогладить\nпогладила(-а) по головке"
        )

    rp_command = args.split()[0]
    rp_action = " ".join(args.split()[1:])

    rp = await rp_commands_service.insert(
        chat_id=message.chat.id,
        command=rp_command,
        action=rp_action,
        type_command=TypeRpCommandEnum.TEXT,
    )

    await message.answer(
        f"Установлена Role-Play команда {rp.command} с действием {rp.action}"
    )


@router.message(Command("all_rp"))
@inject
async def get_all_rp_handler(
    message: Message,
    rp_commands_service: RpCommandsService = Provide[Container.rp_commands_service],
) -> None:
    all_rp = await rp_commands_service.get_all(chat_id=message.chat.id)

    if len(all_rp) == 0:
        await message.reply("В этом чате нет Role-Play команд. Используйте /set_rp")
        return None

    answer_text = "Список всех Role-Play команд чата: \n\n"

    for index, rp in enumerate(all_rp, start=1):
        answer_text += f"{index}. {rp.command} - {rp.action}\n"

    await message.answer(text=answer_text)


@router.message(Command("del_rp"))
@inject
async def delete_rp_handler(
    message: Message,
    command: CommandObject,
    rp_command_service: RpCommandsService = Provide[Container.rp_commands_service],
):
    args = command.args

    if not args:
        raise RpCommandValidateError(
            "не указаны аргументы для удаления. используйте /del_rp <command>"
        )

    await rp_command_service.delete(chat_id=message.chat.id, command=args)

    await message.reply(f"Role-Play команда {args} удалена")


@router.message(RpCommandFilter())
@inject
async def role_play_handler(
    message: Message,
    rp_command: RpCommandDTO,
    user_service: UserService = Provide[Container.user_service],
):
    if not message.text or not message.from_user:
        raise ValueError("message text or user is empty")

    args = message.text.split()
    reply = message.reply_to_message
    name1 = message.from_user.first_name
    name2 = None

    if not reply:
        if len(args) < 2 or "@" not in args[1]:
            return

        username = args[1].lstrip("@")
        user = await user_service.get(find_by=username)

        if not user:
            raise UserNotFound(f"Пользователь с username {username} не найден")
        name2 = user.first_name

    else:
        if not reply.from_user:
            raise ValueError("user is empty")
        name2 = reply.from_user.first_name

    await message.reply(f"{name1} {rp_command.action} {name2}")
