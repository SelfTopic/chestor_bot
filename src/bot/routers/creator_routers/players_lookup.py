from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs
from src.bot.services.admin.player_lookup import PlayerProfile

from ...context import AppContext
from ..types import TextMessage
from .ban_term import ban_term


class AdminProfileArgs(CommandArgs):
    target: str


class AdminProfileHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("admin_profile", AdminProfileArgs)
    query = cmd
    usage = Dialogs.admin.profile.usage()

    def profile_text(self, profile: PlayerProfile) -> str:
        phrases = Dialogs.admin.profile
        user = profile.user
        ghoul = profile.ghoul

        ban = ""
        if user.is_banned:
            ban = self.ctx.text(
                phrases.ban(
                    reason=user.ban_reason or "—",
                    term=ban_term(self.ctx, user.banned_until),
                )
            )

        ghoul_text = ""
        if ghoul:
            kakuja = (
                Dialogs.admin.flag_yes() if ghoul.is_kakuja else Dialogs.admin.flag_no()
            )
            ghoul_text = self.ctx.text(
                phrases.ghoul(
                    level=ghoul.level,
                    rc=ghoul.rc_money,
                    strength=ghoul.strength,
                    dexterity=ghoul.dexterity,
                    speed=ghoul.speed,
                    health=ghoul.health,
                    max_health=ghoul.max_health,
                    regeneration=ghoul.regeneration,
                    hunger=ghoul.hunger,
                    kakuja=self.ctx.text(kakuja),
                )
            )

        status = phrases.banned() if user.is_banned else phrases.active()
        return self.ctx.text(
            phrases.card(
                id=user.telegram_id,
                name=user.full_name,
                username=user.username or "—",
                balance=user.balance,
                status=self.ctx.text(status),
                ban=ban,
                ghoul=ghoul_text,
            )
        )

    async def handle(self) -> None:
        target = self.cmd.parse(self.ctx).target

        profile = await self.ctx.player_lookup_service.get_profile(target)
        if not profile:
            not_found = Dialogs.admin.profile.not_found()
            await self.ctx.message.answer(self.ctx.text(not_found))
            return

        await self.ctx.message.answer(self.profile_text(profile), parse_mode="HTML")

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.ctx.text(self.usage))
            return

        raise exc


class PlayersLookupRouter(BaseRouter[AppContext]):
    handlers = (AdminProfileHandler,)
