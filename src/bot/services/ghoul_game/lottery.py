import asyncio
import logging
import random

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message

from ...exceptions import GhoulNotFoundInDatabase
from ...game_configs import LOTTERY_CONFIG
from ...repositories.lottery import LotteryRepository
from ...services.cooldown import CooldownService
from ...services.dialog import DialogService
from ...services.ghoul import GhoulService
from ...services.media import MediaService
from ...services.user import UserService
from ...types.dep import DepColor, DepResult

logger = logging.getLogger(__name__)

COLOR_TO_FOLDER = {
    "красный": "red",
    "синий": "blue",
    "зелёный": "green",
    "белый": "white",
    "жёлтый": "yellow",
}


class LotteryService:
    def __init__(
        self,
        media_service: MediaService,
        ghoul_service: GhoulService,
        dialog_service: DialogService,
        cooldown_service: CooldownService,
        user_service: UserService,
        lottery_repository: LotteryRepository,
    ):
        self.media_service = media_service
        self.ghoul_service = ghoul_service
        self.dialog_service = dialog_service
        self.cooldown_service = cooldown_service
        self.user_service = user_service
        self.lottery_repository = lottery_repository

    async def execute(
        self, user_id: int, chosen_color: DepColor, bet_amount: int
    ) -> DepResult:
        if bet_amount < LOTTERY_CONFIG.min_bet or bet_amount > LOTTERY_CONFIG.max_bet:
            raise ValueError(
                f"Сумма ставки должна быть от {LOTTERY_CONFIG.min_bet} до {LOTTERY_CONFIG.max_bet}"
            )

        user = await self.user_service.get(find_by=user_id)

        if not user:
            raise ValueError("Пользователь не найден")

        ghoul = await self.ghoul_service.get(find_by=user.telegram_id)

        if not ghoul:
            raise GhoulNotFoundInDatabase()

        if user.balance < bet_amount:
            raise ValueError("Недостаточно денег для такой ставки")

        winning_color = self._get_random_color_by_chance()

        is_won = chosen_color == winning_color

        if is_won:
            multiplier = LOTTERY_CONFIG.get_multiplier(winning_color.value)
            earned = int(bet_amount * multiplier)
            user = await self.user_service.plus_balance(
                telegram_id=user_id, change_balance=earned
            )
        else:
            earned = 0
            user = await self.user_service.minus_balance(
                telegram_id=user_id, change_balance=bet_amount
            )

        folder_name = COLOR_TO_FOLDER.get(winning_color.value, "red")
        video_path = await self.media_service.get_random_lottery_video(
            color_folder=folder_name
        )
        video_file_id = None

        lottery_record = await self.lottery_repository.insert(
            telegram_id=user_id,
            bet_amount=bet_amount,
            chosen_color=chosen_color.value,
            winning_color=winning_color.value,
            is_won=is_won,
            earned=earned if is_won else -bet_amount,
            video_file_id=video_file_id,
        )

        return DepResult(
            ghoul=ghoul,
            user=user,
            bet_amount=bet_amount,
            chosen_color=chosen_color,
            winning_color=winning_color,
            is_won=is_won,
            earned=earned if is_won else -bet_amount,
            video_file_id=video_file_id,
        )

    def _get_random_color_by_chance(self) -> DepColor:
        """Выбрать случайный цвет с учётом шансов выпадения"""
        colors = LOTTERY_CONFIG.colors
        if not colors:
            raise ValueError("Список цветов для лотереи не может быть пустым")
        chances = [LOTTERY_CONFIG.get_chance(color) for color in colors]

        chosen_color_str = random.choices(colors, weights=chances, k=1)[0]
        return DepColor(chosen_color_str)

    def parse_color(self, color_str: str) -> DepColor:
        color_str = color_str.lower().strip()

        for color in DepColor:
            if color.value in color_str:
                return color

        raise ValueError(
            f"Неизвестный цвет '{color_str}'. Используйте: {', '.join(c.value for c in DepColor)}"
        )

    async def send_answer(
        self, message: Message, dep_result: DepResult
    ) -> Message | None:
        folder_name = COLOR_TO_FOLDER.get(dep_result.winning_color.value, "red")
        video_path = await self.media_service.get_random_lottery_video(
            color_folder=folder_name
        )

        if not video_path:
            if dep_result.is_won:
                multiplier = LOTTERY_CONFIG.get_multiplier(
                    dep_result.winning_color.value
                )
                text = self.dialog_service.text(
                    key="lottery_win",
                    chosen_color=dep_result.chosen_color.value,
                    winning_color=dep_result.winning_color.value,
                    bet=dep_result.bet_amount,
                    earned=dep_result.earned,
                    balance=dep_result.user.balance,
                    multiplier=f"{multiplier}x",
                )
            else:
                text = self.dialog_service.text(
                    key="lottery_lose",
                    chosen_color=dep_result.chosen_color.value,
                    winning_color=dep_result.winning_color.value,
                    bet=dep_result.bet_amount,
                    balance=dep_result.user.balance,
                )
            return await message.reply(text=text)

        try:
            if dep_result.video_file_id:
                video_message = await message.reply_animation(
                    animation=dep_result.video_file_id
                )
            else:
                video_message = await message.reply_animation(
                    animation=FSInputFile(video_path)
                )

        except TelegramBadRequest:
            video_message = await message.reply_animation(
                animation=FSInputFile(video_path)
            )

            if not video_message.animation:
                raise

            await self.media_service.update_telegram_file_id(
                path=str(video_path), new_file_id=video_message.animation.file_id
            )

        animation_duration = (
            video_message.animation.duration if video_message.animation else 2
        )

        await asyncio.sleep(animation_duration + 1)

        if dep_result.is_won:
            multiplier = LOTTERY_CONFIG.get_multiplier(dep_result.winning_color.value)
            text = self.dialog_service.text(
                key="lottery_win",
                chosen_color=dep_result.chosen_color.value,
                winning_color=dep_result.winning_color.value,
                bet=dep_result.bet_amount,
                earned=dep_result.earned,
                balance=dep_result.user.balance,
                multiplier=f"{multiplier}x",
            )
        else:
            text = self.dialog_service.text(
                key="lottery_lose",
                chosen_color=dep_result.chosen_color.value,
                winning_color=dep_result.winning_color.value,
                bet=dep_result.bet_amount,
                balance=dep_result.user.balance,
            )

        return await message.reply(text=text)


__all__ = ["LotteryService"]
