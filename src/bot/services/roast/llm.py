import asyncio
from typing import Any

import aiohttp

# Провайдер отвечает 429 при всплеске токенов в минуту и советует повторить через пару секунд.
RETRY_STATUSES = (429, 503)


class LlmError(Exception):
    pass


class LlmClient:
    def __init__(self, base_url: str, api_key: str, *, retry_delay: float = 2.5) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._retry_delay = retry_delay
        self._session: aiohttp.ClientSession | None = None

    async def complete(
        self, model: str, system: str, user: str, *, max_tokens: int, temperature: float
    ) -> str:
        # Одна сессия на процесс: соединение с провайдером переиспользуется, а TLS-рукопожатие
        # стоит дороже самого короткого ответа модели.
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Qwen3 без этого флага тратит весь лимит на скрытые рассуждения и отвечает пусто.
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = await self._post(self._session, model, body)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError(f"{model}: неожиданный ответ {str(data)[:200]}") from exc
        if not isinstance(content, str):
            raise LlmError(f"{model}: пустой ответ")
        return content.strip()

    async def _post(self, session: aiohttp.ClientSession, model: str, body: dict[str, Any]) -> Any:
        for attempt in (1, 2):
            try:
                async with session.post(self._url, json=body) as response:
                    if response.status == 200:
                        return await response.json()
                    error = f"{model}: HTTP {response.status} {(await response.text())[:200]}"
                    if attempt == 2 or response.status not in RETRY_STATUSES:
                        raise LlmError(error)
            except aiohttp.ClientError as exc:
                raise LlmError(f"{model}: {exc}") from exc
            await asyncio.sleep(self._retry_delay)
        raise AssertionError("unreachable")

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
