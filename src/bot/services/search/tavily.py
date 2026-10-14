from dataclasses import dataclass
from typing import Any

import aiohttp

TAVILY_URL = "https://api.tavily.com/search"


class TavilyError(Exception):
    pass


@dataclass(frozen=True)
class Fragment:
    title: str
    content: str
    url: str


class TavilyClient:
    def __init__(self, api_key: str, *, url: str = TAVILY_URL) -> None:
        self._url = url
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def search(self, query: str, *, max_results: int) -> list[Fragment]:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        body = {"query": query, "search_depth": "basic", "max_results": max_results}
        try:
            async with self._session.post(self._url, json=body) as response:
                if response.status != 200:
                    raise TavilyError(f"HTTP {response.status} {(await response.text())[:200]}")
                data = await response.json()
        except aiohttp.ClientError as exc:
            raise TavilyError(str(exc)) from exc
        return [self._fragment(item) for item in self._results(data)]

    def _results(self, data: Any) -> list[dict[str, Any]]:
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise TavilyError(f"неожиданный ответ {str(data)[:200]}")
        return [item for item in results if isinstance(item, dict)]

    def _fragment(self, item: dict[str, Any]) -> Fragment:
        return Fragment(
            title=str(item.get("title") or ""),
            content=str(item.get("content") or ""),
            url=str(item.get("url") or ""),
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
