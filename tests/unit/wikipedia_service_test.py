from unittest.mock import patch

from src.bot.services.wikipedia import WikipediaService, WikipediaSummary


class _FakeResponse:
    def __init__(self, status, json_data=None):
        self.status = status
        self._json_data = json_data or {}

    async def json(self):
        return self._json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    def __init__(self, response):
        self._response = response

    def get(self, url):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


async def test_get_summary_success():
    response = _FakeResponse(
        200,
        {
            "extract": "Тестовое описание",
            "content_urls": {"desktop": {"page": "https://ru.wikipedia.org/wiki/Тест"}},
        },
    )
    with patch("aiohttp.ClientSession", return_value=_FakeSession(response)):
        result = await WikipediaService().get_summary("тест")

    assert result == WikipediaSummary(
        extract="Тестовое описание",
        url="https://ru.wikipedia.org/wiki/Тест",
    )


async def test_get_summary_not_found():
    response = _FakeResponse(404)
    with patch("aiohttp.ClientSession", return_value=_FakeSession(response)):
        result = await WikipediaService().get_summary("несуществующееслово")

    assert result is None


async def test_get_summary_missing_extract():
    response = _FakeResponse(200, {"content_urls": {"desktop": {"page": "https://x"}}})
    with patch("aiohttp.ClientSession", return_value=_FakeSession(response)):
        result = await WikipediaService().get_summary("слово")

    assert result is None


async def test_get_summary_network_error():
    class _RaisingSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def get(self, url):
            raise TimeoutError()

    with patch("aiohttp.ClientSession", return_value=_RaisingSession()):
        result = await WikipediaService().get_summary("слово")

    assert result is None
