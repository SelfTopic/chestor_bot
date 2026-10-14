import asyncio
import logging
import math
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

from src.bot.exceptions import SearchCooldown, SearchLimitReached, SearchUnavailable

from ..llm import LlmClient, LlmError
from .tavily import Fragment, TavilyClient, TavilyError

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"
FRAGMENTS = 5


class SearchService:
    def __init__(
        self,
        llm: LlmClient,
        tavily: TavilyClient,
        *,
        enabled: bool,
        model: str,
        daily_limit: int,
        cooldown: float,
        timeout: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._llm = llm
        self._tavily = tavily
        self._enabled = enabled
        self._model = model
        self._daily_limit = daily_limit
        self._cooldown = cooldown
        self._timeout = timeout
        self._clock = clock
        self._asked_at: dict[int, float] = {}
        self._spent_on = date.today()
        self._spent = 0

    def reserve(self, telegram_id: int) -> None:
        if not self._enabled:
            raise SearchUnavailable()

        now = self._clock()
        self._asked_at = {
            user: at for user, at in self._asked_at.items() if now - at < self._cooldown
        }
        asked_at = self._asked_at.get(telegram_id)
        if asked_at is not None:
            raise SearchCooldown(math.ceil(self._cooldown - (now - asked_at)))

        today = date.today()
        if today != self._spent_on:
            self._spent_on, self._spent = today, 0
        if self._spent >= self._daily_limit:
            raise SearchLimitReached()

        self._spent += 1
        self._asked_at[telegram_id] = now

    async def answer(self, query: str) -> str | None:
        try:
            async with asyncio.timeout(self._timeout):
                fragments = await self._tavily.search(query, max_results=FRAGMENTS)
                return await self._llm.complete(
                    self._model,
                    PROMPT_PATH.read_text("utf-8").strip(),
                    self._request(query, fragments),
                    max_tokens=300,
                    temperature=0.3,
                )
        except (TavilyError, LlmError, TimeoutError):
            logger.warning("Поиск не ответил на %r", query, exc_info=True)
            return None

    def _request(self, query: str, fragments: list[Fragment]) -> str:
        found = "\n\n".join(
            f"[{number}] {fragment.title}\n{fragment.content}"
            for number, fragment in enumerate(fragments, 1)
        )
        return f"Вопрос: {query}\n\nФрагменты:\n{found}"

    async def close(self) -> None:
        await self._tavily.close()
