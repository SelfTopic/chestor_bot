"""VideoCutterService: настоящий ffmpeg на коротком синтетическом ролике.

«Гифка» для Telegram — это MP4 без звука: так сохраняется исходное качество, а
настоящий GIF (256 цветов) выходил мыльным."""

import json
import shutil
import subprocess

import pytest

from src.bot.services.video.cutter import VideoCutterService

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="нужен ffmpeg")


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "Season_1_Episode_1.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=24:duration=4",
            "-f", "lavfi", "-i", "sine=duration=4",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
    )  # fmt: skip
    return path


def streams(path) -> list[dict]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
    )
    return json.loads(probe.stdout)["streams"]


async def test_gif_is_silent_h264_in_source_resolution(tmp_path, source):
    out = await VideoCutterService().cut_video_async(
        source, tmp_path / "gif.mp4", "00:01", "00:03", as_animation=True
    )

    (video,) = streams(out)
    assert video["codec_type"] == "video" and video["codec_name"] == "h264"
    assert (video["width"], video["height"]) == (320, 240)


async def test_video_cut_keeps_sound(tmp_path, source):
    out = await VideoCutterService().cut_video_async(
        source, tmp_path / "video.mp4", "00:01", "00:03"
    )

    assert sorted(s["codec_type"] for s in streams(out)) == ["audio", "video"]


def test_every_cut_gets_its_own_mp4():
    cutter = VideoCutterService()
    paths = [
        cutter.generate_output_path("Season_1_Episode_1.mp4", is_gif=is_gif)
        for is_gif in (False, False, True)
    ]

    assert len(set(paths)) == 3
    assert all(path.suffix == ".mp4" for path in paths)
