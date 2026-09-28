import aiohttp


class LlmError(Exception):
    pass


class LlmClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
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
        try:
            async with self._session.post(self._url, json=body) as response:
                if response.status != 200:
                    raise LlmError(f"{model}: HTTP {response.status} {(await response.text())[:200]}")
                data = await response.json()
        except aiohttp.ClientError as exc:
            raise LlmError(f"{model}: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError(f"{model}: неожиданный ответ {str(data)[:200]}") from exc
        if not isinstance(content, str):
            raise LlmError(f"{model}: пустой ответ")
        return content.strip()

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
