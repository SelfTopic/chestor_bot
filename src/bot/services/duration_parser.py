# Сервис для парсинга строкового значения времени

import re

from src.bot.exceptions import DurationParseError
from src.bot.types import Duration
from src.bot.utils import parse_seconds


class DurationParser:
    """Сервис для парсинга строкового значения времени

    Example:
        parser = DurationParser()
        result = parser.parse("5 минут")
        total_seconds = result.total_seconds # 300
        minutes = result.minutes_remaining # 5

    """

    _UNIT_GROUPS: dict[int, list[str]] = {
        # seconds
        1: [
            "с",
            "сек",
            "секунд",
            "секунда",
            "секунды",
            "s",
            "sec",
            "secs",
            "second",
            "seconds",
        ],
        # minutes
        60: [
            "м",
            "мин",
            "минута",
            "минуты",
            "минут",
            "m",
            "min",
            "mins",
            "minute",
            "minutes",
        ],
        # hours
        3600: [
            "ч",
            "час",
            "часа",
            "часов",
            "h",
            "hr",
            "hrs",
            "hour",
            "hours",
        ],
        # days
        86400: [
            "д",
            "дн",
            "день",
            "дня",
            "дней",
            "сут",
            "сутки",
            "d",
            "day",
            "days",
        ],
        # weeks
        604800: [
            "н",
            "нед",
            "неделя",
            "недели",
            "недель",
            "w",
            "wk",
            "wks",
            "week",
            "weeks",
        ],
    }

    UNITS: dict[str, int] = {
        alias: seconds for seconds, aliases in _UNIT_GROUPS.items() for alias in aliases
    }

    FOREVER_KEYWORDS = {"навсегда", "пермамент", "пермач", "пожизненн"}

    TIME_UNITS_PATTERN = r"""
    (?P<value>\d+(?:[.,]\d+)?)
    \s*
    (?P<unit>
        с|сек(?:унд[аы]?|)|seconds?|secs?|s|
        м|мин(?:ут[аы]?|)|minutes?|mins?|m|
        ч|час(?:а|ов)?|hours?|hrs?|hr|h|
        д|дн|день|дня|дней|сут(?:ки)?|days?|d|
        н|нед(?:еля|ели|ель)?|weeks?|wks?|wk|w
    )
    \b
    """

    @classmethod
    def parse_string(cls, value: str) -> Duration:
        """Парсит строку в компоненты времени TimeComponents

        Args:
            value (str): строковое значение времени, например (5 минут)

        Raises:
            DurationParseError:

        Returns:
            Duration

        """

        if not value or not value.strip():
            raise DurationParseError("Value is empty")

        text = value.strip().lower()

        # Проверка на "навсегда"
        if text in cls.FOREVER_KEYWORDS:
            return Duration(
                components=parse_seconds(total_seconds=0),
                raw=text,
            )

        total_seconds = 0
        position = 0

        pattern = re.compile(cls.TIME_UNITS_PATTERN, re.VERBOSE)

        for match in pattern.finditer(text):
            if match.start() != position and text[position : match.start()].strip():
                raise DurationParseError()

            raw_value = match.group("value")
            raw_unit = match.group("unit")

            try:
                number = float(raw_value.replace(",", "."))
            except ValueError:
                raise DurationParseError()

            unit_seconds = cls.UNITS.get(raw_unit)
            if unit_seconds is None:
                raise DurationParseError()

            total_seconds += number * unit_seconds
            position = match.end()

        if total_seconds == 0 and not any(
            text.startswith(word) for word in cls.FOREVER_KEYWORDS
        ):
            raise DurationParseError()

        if text[position:].strip():
            raise DurationParseError()

        return Duration(
            components=parse_seconds(total_seconds=int(total_seconds)),
            raw=text,
        )


if __name__ == "__main__":
    parser = DurationParser()

    result = parser.parse_string("3 дня 12 часов 8 минут")

    print(result)
