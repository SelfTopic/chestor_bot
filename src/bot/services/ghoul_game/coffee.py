from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message

from ...exceptions import GhoulNotFoundInDatabase
from ...game_configs import COFFEE_CONFIG
from ...services.cooldown import CooldownService
from ...services.dialog import DialogService
from ...services.ghoul import GhoulService
from ...services.media import MediaService
from ...services.user import UserService
from ...types.coffee import CoffeeResult


class CoffeeService:
    def __init__(
        self,
        media_service: MediaService,
        ghoul_service: GhoulService,
        dialog_service: DialogService,
        cooldown_service: CooldownService,
        user_service: UserService,
    ):
        self.media_service = media_service
        self.ghoul_service = ghoul_service
        self.dialog_service = dialog_service
        self.cooldown_service = cooldown_service
        self.user_service = user_service

    async def execute(self, user_id: int):
        money = COFFEE_CONFIG.award

        ghoul = await self.ghoul_service.coffee(telegram_id=user_id)
        user = await self.user_service.plus_balance(
            telegram_id=user_id, change_balance=money
        )

        return CoffeeResult(ghoul=ghoul, user=user, award=money)

    async def execute_cooldown(self, user_id: int, cooldown_name: str = "COFFEE"):
        cooldown = await self.cooldown_service.get_active_cooldown(
            telegram_id=user_id, cooldown_name=cooldown_name
        )

        cooldown_day = await self.cooldown_service.get_active_cooldown(
            telegram_id=user_id, cooldown_name="COFFEE_DAY"
        )

        if cooldown_day:
            return cooldown_day

        if cooldown:
            if cooldown_day:
                return cooldown_day

            result_cooldown = await self.cooldown_service.set_cooldown(
                telegram_id=user_id, cooldown_type="COFFEE_DAY"
            )
            await self.user_service.minus_balance(
                telegram_id=user_id, change_balance=COFFEE_CONFIG.award
            )
            return result_cooldown

        await self.cooldown_service.set_cooldown(
            telegram_id=user_id, cooldown_type=cooldown_name
        )

        return None

    async def check_snap_limit(self, message: Message):
        ghoul = await self.ghoul_service.get(find_by=message)

        if not ghoul:
            raise GhoulNotFoundInDatabase()

        if ghoul.snap_count < COFFEE_CONFIG.snap_limit:
            text = self.dialog_service.text(key="coffee_snap_limit")
            await message.reply(text=text)
            return False

        return True

    async def send_answer(self, message: Message, coffee_result: CoffeeResult):
        text = self.dialog_service.text(
            key="coffee_accept",
            count=coffee_result.ghoul.coffee_count,
            money=coffee_result.award,
        )

        media = await self.media_service.get_random_gif(collection_string="coffee")

        if not media:
            return await message.reply(text=text)

        try:
            return await message.reply_animation(
                animation=media.telegram_file_id, caption=text
            )

        except TelegramBadRequest:
            my_message = await message.reply_animation(
                animation=FSInputFile(media.path), caption=text
            )

            if not my_message.animation:
                raise

            await self.media_service.update_telegram_file_id(
                path=str(media.path), new_file_id=my_message.animation.file_id
            )

            return my_message
