from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aiohttp import web
from aiohttp.test_utils import TestServer
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.services.roulette import Clip, RouletteVideos, VideoSet
from src.bot.services.roulette.video_set import ARCHIVE, pack
from tests.roulette_fakes import clip_path, fake_render

CLIPS = (Clip(0, 3, 0), Clip(3, 7, 4))


def release(tmp_path: Path) -> Path:
    built = tmp_path / "built"
    for clip in CLIPS:
        fake_render(clip, clip_path(built, clip))
    archive = tmp_path / ARCHIVE
    pack(built, archive)
    return archive


async def test_set_is_downloaded_again_after_a_failed_attempt(tmp_path):
    archive = release(tmp_path)
    requests: list[str] = []

    # Первый запрос — как будто GitHub ещё не выложил релиз.
    async def asset(request: web.Request) -> web.StreamResponse:
        requests.append(request.path)
        if len(requests) == 1:
            raise web.HTTPNotFound()
        return web.FileResponse(archive)

    app = web.Application()
    app.router.add_get(f"/{ARCHIVE}", asset)
    folder = tmp_path / "set"
    async with TestServer(app) as server:
        videos = RouletteVideos(
            async_sessionmaker(),
            VideoSet(str(server.make_url(f"/{ARCHIVE}")), folder),
            spin_path=lambda clip: clip_path(folder, clip),
            executor=lambda: ThreadPoolExecutor(1),
            warm=False,
            retry=0.01,
        )
        videos.start()
        await videos.idle()
        await videos.close()

    assert len(requests) == 2
    assert all(videos.ready(clip) for clip in CLIPS)
    assert not videos.ready(Clip(0, 3, 1))
    assert [path.name for path in folder.parent.iterdir() if path.name.startswith(".")] == []
