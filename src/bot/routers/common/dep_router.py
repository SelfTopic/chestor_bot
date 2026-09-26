import logging

from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError, TelegramBadRequest
from selfrot.filter import Command, HasUser
from selfrot.types import InputFile

from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.services.ghoul_game import LotteryService
from src.bot.services.ghoul_game.lottery import COLOR_TO_FOLDER
from src.bot.types.dep import DepResult

from ...context import AppContext
from ..types import TextUserMessage

logger = logging.getLogger(__name__)


class DepArgs(CommandArgs):
    color: str
    bet: int


class DepnutHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = Command("депнуть", DepArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser()
    format_error = "❌ Неверный формат команды. Используйте: депнуть <цвет> <ставка>"

    def result_text(self, dep_result: DepResult) -> str:
        dialog = self.ctx.dialog_service

        if dep_result.is_won:
            multiplier = LOTTERY_CONFIG.get_multiplier(dep_result.winning_color.value)
            return dialog.text(
                key="lottery_win",
                chosen_color=dep_result.chosen_color.value,
                winning_color=dep_result.winning_color.value,
                bet=dep_result.bet_amount,
                earned=dep_result.earned,
                balance=dep_result.user.balance,
                multiplier=f"{multiplier}x",
            )

        return dialog.text(
            key="lottery_lose",
            chosen_color=dep_result.chosen_color.value,
            winning_color=dep_result.winning_color.value,
            bet=dep_result.bet_amount,
            balance=dep_result.user.balance,
        )

    async def reply_later(self, text: str) -> None:
        # ошибка отложенного ответа не должна попадать в on_error: результат уже
        # записан в БД, а пользователь просто не увидит текст (как у прода)
        try:
            await self.ctx.message.reply(text)
        except Exception:
            logger.error("Failed to send delayed lottery result", exc_info=True)

    async def send_answer(
        self, lottery_service: LotteryService, dep_result: DepResult
    ) -> None:
        """
        Ответ как у прода (LotteryService.send_answer, тег aiogram-final). Разница
        одна: результат после гифки приходит через self.defer (транзакция к тому времени закрыта и
        закоммичена, слот не занят), а не через create_task с sleep в сервисе.
        """
        message = self.ctx.message
        folder_name = COLOR_TO_FOLDER.get(dep_result.winning_color.value, "red")
        video_path = await lottery_service.media_service.get_random_lottery_video(
            color_folder=folder_name
        )

        if not video_path:
            await message.reply(self.result_text(dep_result))
            return

        try:
            if dep_result.video_file_id:
                video_message = await message.reply_animation(
                    animation=dep_result.video_file_id
                )
            else:
                video_message = await message.reply_animation(
                    animation=InputFile.from_path(video_path)
                )

        except TelegramBadRequest:
            video_message = await message.reply_animation(
                animation=InputFile.from_path(video_path)
            )

            if not video_message.animation:
                raise

            await lottery_service.media_service.update_telegram_file_id(
                path=str(video_path), new_file_id=video_message.animation.file_id
            )

        animation_duration = (
            video_message.animation.duration if video_message.animation else 2
        )

        # Пауза ради UX: не спойлерить исход раньше, чем доиграется гифка.
        self.defer(
            self.reply_later,
            self.result_text(dep_result),
            delay=animation_duration + 1,
        )

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)  # неверный формат: CommandArgsError
        lottery_service = self.ctx.lottery_service

        chosen_color = lottery_service.parse_color(color_str=args.color)

        dep_result = await lottery_service.execute(
            user_id=self.ctx.message.user.id,
            chosen_color=chosen_color,
            bet_amount=args.bet,
        )

        await self.send_answer(lottery_service, dep_result)

    async def on_error(self, exc: Exception) -> None:
        # Как у прода: любая ошибка ставки превращается в ответ, бот не молчит. Разница
        # одна: ошибка теперь доходит до DatabaseMiddleware, и если она случилась после
        # списания (например, не отправилась гифка), ставка откатывается вместе с ней.
        message = self.ctx.message

        if isinstance(exc, CommandArgsError):
            await message.reply(self.format_error)
        elif isinstance(exc, ValueError):
            await message.reply(str(exc))
        else:
            logger.error(f"Ошибка при обработке депнуть: {exc}")
            await message.reply("❌ Произошла ошибка при обработке вашей ставки")


class DepRouter(BaseRouter[AppContext]):
    handlers = (DepnutHandler,)
