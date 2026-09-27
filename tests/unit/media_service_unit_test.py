import pytest

from src.bot.exceptions import CollectionNotFoundError
from src.bot.services.media import CollectionParser
from src.bot.types import MediaCollection


def test_parse_known_collection():
    result = CollectionParser.parse("death")
    assert result == MediaCollection.DEATH


@pytest.mark.parametrize(
    "key",
    [
        "welcome gif",
        "welcome photo",
        "welcome video",
        "goodbye gif",
        "goodbye photo",
        "goodbye video",
    ],
)
def test_parse_all_known_keys(key):
    result = CollectionParser.parse(key)
    assert isinstance(result, MediaCollection)


def test_parse_unknown_raises():
    with pytest.raises(CollectionNotFoundError):
        CollectionParser.parse("nonexistent_collection")


def test_parse_empty_string_raises():
    with pytest.raises(CollectionNotFoundError):
        CollectionParser.parse("")
