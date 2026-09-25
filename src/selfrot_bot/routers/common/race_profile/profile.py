import logging

from selfrot import MessageHandler
from selfrot.filter import Command, HasUser, Text

from src.bot.types import Race
from src.database.models import Ghoul, User

from ....context import AppContext
from ....types import UserMessage
from .ghoul_message import BattleStats, plain_profile, rich_profile
from .rich import answer_rich_or_text

logger = logging.getLogger(__name__)


class RaceProfileHandler(MessageHandler[AppContext[UserMessage]]):
    query = (Text("распрофиль", ignore_case=True) | Command("race_profile")) & HasUser()

    async def battle_stats(self, telegram_id: int) -> BattleStats:
        # запросы идут по очереди: у одной AsyncSession параллельные запросы недопустимы
        battles = self.ctx.battle_record_service
        return BattleStats(
            wins=await battles.count_wins_vs_players(telegram_id),
            losses=await battles.count_losses_vs_players(telegram_id),
            total=await battles.count_total_battles_vs_players(telegram_id),
            mob_wins=await battles.count_wins_vs_mobs(telegram_id),
            mob_losses=await battles.count_losses_vs_mobs(telegram_id),
            mob_total=await battles.count_total_battles_vs_mobs(telegram_id),
        )

    async def send_ghoul_profile(self, user: User, ghoul: Ghoul) -> None:
        dialog_service = self.ctx.dialog_service
        ghoul_service = self.ctx.ghoul_service

        if ghoul.is_dead:
            await self.ctx.message.answer(
                dialog_service.text(key="dead_ghoul_profile", name=user.full_name)
            )
            return

        power = ghoul_service.calculate_power(ghoul)
        danger_rank = ghoul_service.get_danger_rank(power)
        stats = await self.battle_stats(ghoul.telegram_id)

        await answer_rich_or_text(
            self.ctx.message,
            rich_profile(user, ghoul, ghoul_service, danger_rank, power, stats),
            lambda: plain_profile(
                dialog_service, user, ghoul, ghoul_service, danger_rank, power, stats
            ),
            what="ghoul profile",
        )

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        race = self.ctx.user_service.race(user.race_bit)
        if not race:
            raise RuntimeError(f"Unknown race bit: {user.race_bit}")

        if race == Race.GHOUL:
            ghoul = await self.ctx.ghoul_service.get(self.ctx.message.user.id)
            if not ghoul:
                logger.error("Ghoul not found in database")
                raise ValueError("Ghoul not found in database")

            await self.send_ghoul_profile(user, ghoul)
            return

        await self.ctx.message.answer(
            self.ctx.dialog_service.text(
                key="profile",
                name=user.full_name,
                race=race.value["name"],
                balance=user.balance,
            )
        )
