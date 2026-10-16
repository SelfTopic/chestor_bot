import asyncio
import contextlib
import logging
import os
import signal
from pathlib import Path

from src.bot.exceptions import MediaToolError


logger = logging.getLogger(__name__)

TOOL_TIMEOUT = 180
# --xff US обходит региональные блокировки постов TikTok с IP в Нидерландах.
YTDLP_FLAGS = ("--no-warnings", "--no-playlist", "--xff", "US")
TOOLS_UPDATE_INTERVAL = 24 * 3600
TOOLS = ("yt-dlp[default,curl-cffi]", "gallery-dl")


async def run(*args: str, timeout: float = TOOL_TIMEOUT) -> str:
    # Своя группа процессов: yt-dlp запускает ffmpeg, и убивать нужно обоих, а не только
    # yt-dlp. Группы других скачиваний это не задевает.
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout)
    except TimeoutError:
        await _kill(process)
        raise MediaToolError(f"timeout: {' '.join(args[:3])}") from None
    except asyncio.CancelledError:
        # Отменённая задача не должна оставить скачивание работать сиротой.
        await _kill(process)
        raise
    if process.returncode != 0:
        lines = err.decode(errors="replace").strip().splitlines()
        raise MediaToolError(lines[-1] if lines else f"exit code {process.returncode}")
    return out.decode(errors="replace")


async def _kill(process: asyncio.subprocess.Process) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    await process.wait()


# yt-dlp и gallery-dl живут в своём venv и обновляются в нём: сайты ломают скачивание
# чаще, чем выходит новый образ бота, а зависимости самого бота это не трогает.
class MediaToolsUpdater:
    def __init__(self, tools: Path) -> None:
        self._tools = tools

    async def tick(self) -> None:
        pip = str(self._tools / "pip")
        await run(pip, "install", "-q", "-U", *TOOLS, timeout=600)
        version = (await run(str(self._tools / "yt-dlp"), "--version")).strip()
        logger.info("yt-dlp и gallery-dl обновлены (yt-dlp %s)", version)
