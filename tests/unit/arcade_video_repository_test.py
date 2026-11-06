from src.bot.repositories import ArcadeVideoRepository


async def test_video_cache(session):
    videos = ArcadeVideoRepository(session)

    await videos.save("crash/241.mp4@1", "old")
    await videos.save("crash/241.mp4@1", "new")
    assert await videos.file_id("crash/241.mp4@1") == "new"

    await videos.forget("crash/241.mp4@1")
    assert await videos.file_id("crash/241.mp4@1") is None
