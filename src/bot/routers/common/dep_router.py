import logging

from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError, TelegramBadRequest
from selfrot.filter import Command, HasUser
from selfrot.types import InputFile

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    BetOutOfRange,
    LotteryPlayerMissing,
    NotEnoughMoneyForBet,
    UnknownLotteryColor,
)
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.services.ghoul_game import LotteryService
from src.bot.services.ghoul_game.lottery import COLOR_TO_FOLDER
from src.bot.types.dep import DepColor, DepResult

from ...context import AppContext
from ..types import TextUserMessage

logger = logging.getLogger(__name__)


class DepArgs(CommandArgs):
    color: str
    bet: int


class DepnutHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = Command("депнуть", DepArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser()
    usage = Dialogs.lottery.usage()
    failed = Dialogs.lottery.failed()

    def result_line(self, dep_result: DepResult) -> Line:
        if dep_result.is_won:
            multiplier = LOTTERY_CONFIG.get_multiplier(dep_result.winning_color.value)
            return Dialogs.lottery.win(
                chosen_color=dep_result.chosen_color.value,
                winning_color=dep_result.winning_color.value,
                bet=dep_result.bet_amount,
                earned=dep_result.earned,
                balance=dep_result.user.balance,
                multiplier=f"{multiplier}x",
            )

        return Dialogs.lottery.lose(
            chosen_color=dep_result.chosen_color.value,
            winning_color=dep_result.winning_color.value,
            bet=dep_result.bet_amount,
            balance=dep_result.user.balance,
        )

    async def reply_later(self, line: Line) -> None:
        # Ошибка отложенного ответа не идёт в on_error: ставка уже записана в БД.
        try:
            await self.ctx.say(line, reply=True)
        except Exception:
            logger.error("Failed to send delayed lottery result", exc_info=True)

    async def send_answer(
        self, lottery_service: LotteryService, dep_result: DepResult
    ) -> None:
        message = self.ctx.message
        folder_name = COLOR_TO_FOLDER.get(dep_result.winning_color.value, "red")
        video_path = await lottery_service.media_service.get_random_lottery_video(
            color_folder=folder_name
        )

        if not video_path:
            await self.ctx.say(self.result_line(dep_result), reply=True)
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

        # Пауза, чтобы итог не пришёл раньше, чем доиграет гифка.
        self.defer(
            self.reply_later,
            self.result_line(dep_result),
            delay=animation_duration + 1,
        )

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        lottery_service = self.ctx.lottery_service

        chosen_color = lottery_service.parse_color(color_str=args.color)

        dep_result = await lottery_service.execute(
            user_id=self.ctx.message.user.id,
            chosen_color=chosen_color,
            bet_amount=args.bet,
        )

        await self.send_answer(lottery_service, dep_result)

    def error_line(self, exc: Exception) -> Line:
        match exc:
            case CommandArgsError():
                return self.usage
            case BetOutOfRange(min_bet=min_bet, max_bet=max_bet):
                return Dialogs.lottery.bet_out_of_range(
                    min_bet=min_bet, max_bet=max_bet
                )
            case NotEnoughMoneyForBet():
                return Dialogs.lottery.not_enough_money()
            case LotteryPlayerMissing():
                return Dialogs.lottery.player_missing()
            case UnknownLotteryColor(color=color):
                colors = ", ".join(c.value for c in DepColor)
                return Dialogs.lottery.unknown_color(color=color, colors=colors)
            case _:
                logger.error(f"Ошибка при обработке депнуть: {exc}")
                return self.failed

    async def on_error(self, exc: Exception) -> None:
        await self.ctx.say(self.error_line(exc), reply=True)


class DepRouter(BaseRouter[AppContext]):
    handlers = (DepnutHandler,)
