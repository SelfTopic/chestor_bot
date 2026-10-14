import asyncio
import logging
from pathlib import Path

from src.bot.exceptions import MediaToolError

from .ticker import Ticker

logger = logging.getLogger(__name__)

TOOL_TIMEOUT = 180
# --xff US обходит региональные блокировки постов TikTok с IP в Нидерландах.
YTDLP_FLAGS = ("--no-warnings", "--no-playlist", "--xff", "US")
TOOLS_UPDATE_INTERVAL = 24 * 3600
TOOLS = ("yt-dlp[default,curl-cffi]", "gallery-dl")


async def run(*args: str, timeout: float = TOOL_TIMEOUT) -> str:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise MediaToolError(f"timeout: {' '.join(args[:3])}") from None
    except asyncio.CancelledError:
        # Отменённая задача не должна оставить скачивание работать сиротой.
        process.kill()
        await process.wait()
        raise
    if process.returncode != 0:
        lines = err.decode(errors="replace").strip().splitlines()
        raise MediaToolError(lines[-1] if lines else f"exit code {process.returncode}")
    return out.decode(errors="replace")


# yt-dlp и gallery-dl живут в своём venv и обновляются в нём: сайты ломают скачивание
# чаще, чем выходит новый образ бота, а зависимости самого бота это не трогает.
class MediaToolsUpdater(Ticker):
    def __init__(self, tools: Path, interval_seconds: float = TOOLS_UPDATE_INTERVAL) -> None:
        super().__init__(interval_seconds)
        self._tools = tools

    async def tick(self) -> None:
        pip = str(self._tools / "pip")
        await run(pip, "install", "-q", "-U", *TOOLS, timeout=600)
        version = (await run(str(self._tools / "yt-dlp"), "--version")).strip()
        logger.info("yt-dlp и gallery-dl обновлены (yt-dlp %s)", version)
