from src.bot.game_configs import STATS, StatKey
from src.bot.types import KaguneType, Race

from .line import Line, LineText
from .tree import Dialogs

KAGUNE_NAMES: dict[KaguneType, Line] = {
    KaguneType.UKAKU: Dialogs.vocab.kagune.ukaku(),
    KaguneType.KOUKAKU: Dialogs.vocab.kagune.koukaku(),
    KaguneType.RINKAKU: Dialogs.vocab.kagune.rinkaku(),
    KaguneType.BIKAKU: Dialogs.vocab.kagune.bikaku(),
}

RACE_NAMES: dict[Race, Line] = {
    Race.HUMAN: Dialogs.vocab.race.human(),
    Race.GHOUL: Dialogs.vocab.race.ghoul(),
    Race.CCG: Dialogs.vocab.race.ccg(),
}

STAT_NAMES: dict[str, Line] = {
    "strength": Dialogs.vocab.stat.strength(),
    "dexterity": Dialogs.vocab.stat.dexterity(),
    "speed": Dialogs.vocab.stat.speed(),
    "max_health": Dialogs.vocab.stat.max_health(),
    "health": Dialogs.vocab.stat.health(),
    "regeneration": Dialogs.vocab.stat.regeneration(),
}

HUNGER_NAMES: dict[str, Line] = {
    "full": Dialogs.vocab.hunger.full(),
    "light": Dialogs.vocab.hunger.light(),
    "strong": Dialogs.vocab.hunger.strong(),
    "deadly": Dialogs.vocab.hunger.deadly(),
}

STAT_EMOJI = dict(STATS)


def stat_label(text: LineText, key: StatKey) -> str:
    return f"{STAT_EMOJI[key]}{text(STAT_NAMES[key])}"
