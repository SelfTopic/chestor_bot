from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command, HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import DurationParseError, PromoNameTaken
from src.bot.services import DurationParser
from src.bot.game_configs import StatKey
from src.bot.services.promo import (
    ChestonReward,
    Granted,
    LevelProgressReward,
    RcReward,
    Reward,
    StatReward,
)

from ...context import AppContext
from ..promo_rewards import reward_lines
from ..types import TextUserMessage

MOSCOW = ZoneInfo("Europe/Moscow")
CHESTON_WORDS = ("честоны", "честон", "чс", "cheston")
RC_WORDS = ("рс", "rc", "клетки")
PROGRESS_WORDS = ("прогресс", "опыт", "xp")
STAT_WORDS: dict[str, StatKey] = {
    "сила": "strength",
    "ловкость": "dexterity",
    "скорость": "speed",
    "здоровье": "max_health",
    "хп": "max_health",
    "реген": "regeneration",
    "регенерация": "regeneration",
}


class PromoSpecError(Exception):
    def __init__(self, line: str | None = None) -> None:
        super().__init__(line)
        self.line = line


@dataclass(frozen=True)
class PromoSpec:
    activations: int
    lifetime: timedelta | None
    rewards: list[Reward]


def positive(word: str, line: str) -> int:
    if not word.isdigit() or int(word) == 0:
        raise PromoSpecError(line)
    return int(word)


def parse_reward(line: str) -> Reward:
    words = line.casefold().split()
    if len(words) == 2 and words[0] in CHESTON_WORDS:
        return ChestonReward(amount=positive(words[1], line))
    if len(words) == 2 and words[0] in RC_WORDS:
        return RcReward(amount=positive(words[1], line))
    if len(words) == 2 and words[0] in PROGRESS_WORDS:
        return LevelProgressReward(percent=positive(words[1].removesuffix("%"), line))
    if len(words) == 2 and words[0] in STAT_WORDS:
        return StatReward(stat=STAT_WORDS[words[0]], amount=positive(words[1], line))
    raise PromoSpecError(line)


def parse_lifetime(text: str) -> timedelta | None:
    if not text:
        return None
    try:
        seconds = DurationParser.parse_string(text).components.total_seconds
    except DurationParseError:
        raise PromoSpecError(text)
    return timedelta(seconds=seconds) if seconds else None


# Без строк наград первая строка — короткая форма: CheSton, активации, срок.
def parse_spec(spec: str) -> PromoSpec:
    head, *lines = spec.splitlines() or [""]
    words = head.split()
    reward_rows = [line.strip() for line in lines if line.strip()]
    numbers = 1 if reward_rows else 2
    if len(words) < numbers or not all(word.isdigit() for word in words[:numbers]):
        raise PromoSpecError()

    lifetime = parse_lifetime(" ".join(words[numbers:]))
    rewards: list[Reward]
    if reward_rows:
        rewards = [parse_reward(line) for line in reward_rows]
        activations = positive(words[0], head)
    else:
        rewards = [ChestonReward(amount=positive(words[0], head))]
        activations = positive(words[1], head)
    return PromoSpec(activations, lifetime, rewards)


class CreatePromoArgs(CommandArgs):
    name: str
    spec: Rest = ""


class CreatePromoHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = Command("промо", CreatePromoArgs, prefixes="+", ignore_case=True)
    query = cmd & HasUser()
    usage = Dialogs.admin.promo.usage()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        spec = parse_spec(args.spec)
        promo = await self.ctx.promo_service.create(
            args.name,
            spec.rewards,
            spec.activations,
            spec.lifetime,
            created_by=self.ctx.message.user.id,
        )

        phrases = Dialogs.admin.promo
        if promo.expires_at is None:
            until = phrases.forever()
        else:
            expires = promo.expires_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(MOSCOW)
            until = phrases.until(date=expires.strftime("%d.%m.%Y %H:%M"))
        created = phrases.created(
            name=promo.name,
            activations=promo.activations_limit,
            until=self.ctx.text(until),
            rewards=reward_lines(self.ctx, [Granted(reward) for reward in spec.rewards]),
        )
        await self.ctx.say(created, reply=True)

    async def on_error(self, exc: Exception) -> None:
        line: Line
        match exc:
            case CommandArgsError() | PromoSpecError(line=None):
                line = self.usage
            case PromoSpecError(line=str(bad)):
                line = Dialogs.admin.promo.bad_line(line=bad)
            case PromoNameTaken(name=name):
                line = Dialogs.admin.promo.name_taken(name=name)
            case _:
                raise exc
        await self.ctx.say(line, reply=True)


class PromoAdminRouter(BaseRouter[AppContext]):
    handlers = (CreatePromoHandler,)
