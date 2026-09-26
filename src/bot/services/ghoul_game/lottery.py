import logging
import random

from ...game_configs import LOTTERY_CONFIG
from ...repositories.lottery import LotteryRepository
from ...services.cooldown import CooldownService
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
        cooldown_service: CooldownService,
        user_service: UserService,
        lottery_repository: LotteryRepository,
    ):
        self.media_service = media_service
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

        if user.balance < bet_amount:
            raise ValueError("Недостаточно денег для такой ставки")

        winning_color = self._get_random_color_by_chance()

        is_won = chosen_color == winning_color

        if is_won:
            multiplier = LOTTERY_CONFIG.get_multiplier(winning_color.value)
            earned = int(bet_amount * multiplier)
            user = await self.user_service.plus_balance(
                telegram_id=user_id, change_balance=earned, log="lottery win"
            )
        else:
            earned = 0
            user = await self.user_service.minus_balance(
                telegram_id=user_id, change_balance=bet_amount, log="lottery bet"
            )

        # Видео подбирает роутер, в записи file_id пока не бывает (как у прода).
        video_file_id = None

        await self.lottery_repository.insert(
            telegram_id=user_id,
            bet_amount=bet_amount,
            chosen_color=chosen_color.value,
            winning_color=winning_color.value,
            is_won=is_won,
            earned=earned if is_won else -bet_amount,
            video_file_id=video_file_id,
        )

        return DepResult(
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


__all__ = ["LotteryService"]
