import pytest

from src.bot.exceptions import (
    CollectionNotFoundError,
    InvalidMediaRequestError,
    ValidationMediaError,
)
from src.bot.services.media import CollectionParser, MediaService
from src.bot.types import MediaCollection, MediaDownloadType, MediaSaveRequest


def test_parse_known_collection():
    result = CollectionParser.parse("coffee")
    assert result == MediaCollection.COFFEE


def test_parse_snap():
    result = CollectionParser.parse("snap")
    assert result == MediaCollection.SNAP_FINGER


def test_parse_snap_finger_alias():
    result = CollectionParser.parse("snap finger")
    assert result == MediaCollection.SNAP_FINGER


@pytest.mark.parametrize(
    "key",
    [
        "kagune ukaku",
        "kagune koukaku",
        "kagune rinkaku",
        "kagune bikaku",
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


@pytest.fixture
def media_service():
    """MediaService с замоканными зависимостями — нам нужны только чистые методы."""
    from unittest.mock import MagicMock

    return MediaService(downloader=MagicMock(), media_repository=MagicMock())


def test_validate_raises_without_bytes(media_service):
    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        collection=MediaCollection.COFFEE,
        original_filename="test.mp4",
        bytes_media=None,
    )
    with pytest.raises(ValidationMediaError, match="байты"):
        media_service._validate_media_request(req)


def test_validate_raises_without_collection(media_service):
    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        original_filename="test.mp4",
        bytes_media=b"data",
        collection=None,
    )
    with pytest.raises(ValidationMediaError, match="коллекци"):
        media_service._validate_media_request(req)


def test_validate_raises_without_filename(media_service):
    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        collection=MediaCollection.COFFEE,
        bytes_media=b"data",
        original_filename=None,
    )
    with pytest.raises(ValidationMediaError, match="имя"):
        media_service._validate_media_request(req)


def test_validate_raises_without_type(media_service):
    req = MediaSaveRequest(
        collection=MediaCollection.COFFEE,
        bytes_media=b"data",
        original_filename="test.mp4",
        type_media=None,
    )
    with pytest.raises(ValidationMediaError, match="тип"):
        media_service._validate_media_request(req)


def test_validate_passes_with_full_request(media_service):
    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        collection=MediaCollection.COFFEE,
        bytes_media=b"data",
        original_filename="test.mp4",
    )
    media_service._validate_media_request(req)


def test_generate_path_raises_without_collection(media_service):
    req = MediaSaveRequest(type_media=MediaDownloadType.ANIMATION, collection=None)
    with pytest.raises(InvalidMediaRequestError):
        media_service._generate_path(req)


def test_generate_path_raises_without_type(media_service):
    req = MediaSaveRequest(type_media=None, collection=MediaCollection.COFFEE)
    with pytest.raises(InvalidMediaRequestError):
        media_service._generate_path(req)


def test_generate_path_returns_path_object(media_service):
    from pathlib import Path

    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        collection=MediaCollection.COFFEE,
    )
    result = media_service._generate_path(req)
    assert isinstance(result, Path)


def test_generate_path_kagune_uses_animation(media_service):
    req = MediaSaveRequest(
        type_media=MediaDownloadType.ANIMATION,
        collection=MediaCollection.UPGRADE_KAGUNE_UKAKU,
    )
    result = media_service._generate_path(req)
    assert MediaDownloadType.ANIMATION.value in str(result)
