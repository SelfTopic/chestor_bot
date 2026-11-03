import json
import subprocess

import pytest

from src.bot.game_configs import CHART_CONFIG
from src.bot.services.chart_game import render_growth_video
from src.bot.services.chart_game import growth_video
from src.bot.services.chart_game.crash_video import render_crash_video
from src.bot.services.chart_game.opening_video import render_opening_video
from src.bot.services.chart_game.chart import HEIGHT, WIDTH


def video_size_and_duration(video):
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(video),
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    info = json.loads(probe.stdout)
    stream = info["streams"][0]
    return (stream["width"], stream["height"]), float(info["format"]["duration"])


def test_growth_video_lasts_countdown_growth_and_late_edit(tmp_path):
    video = tmp_path / "growth.mp4"

    render_growth_video(video, fps=1, workers=1)

    size, duration = video_size_and_duration(video)
    expected = (
        CHART_CONFIG.countdown_seconds
        + CHART_CONFIG.growth_seconds
        + CHART_CONFIG.late_edit_seconds
    )
    assert size == (WIDTH, HEIGHT)
    assert abs(duration - expected) < 1
    assert list(tmp_path.iterdir()) == [video]


@pytest.mark.parametrize(
    "render",
    [
        lambda path: render_opening_video(path, fps=2),
        lambda path: render_crash_video(path, 294, fps=2),
    ],
)
def test_preparation_videos_last_preparation_and_late_edit(tmp_path, render):
    video = tmp_path / "preparation.mp4"

    render(video)

    size, duration = video_size_and_duration(video)
    expected = CHART_CONFIG.preparation_seconds + CHART_CONFIG.late_edit_seconds
    assert size == (WIDTH, HEIGHT)
    assert abs(duration - expected) < 1


def test_failed_encoding_leaves_no_file(tmp_path, monkeypatch):
    video = tmp_path / "growth.mp4"
    real_popen = subprocess.Popen

    def broken_ffmpeg(args, **kwargs):
        return real_popen(["sh", "-c", "cat > /dev/null; exit 1"], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", broken_ffmpeg)
    monkeypatch.setattr(growth_video, "frame_count", lambda fps: 3)

    with pytest.raises(subprocess.CalledProcessError):
        render_growth_video(video, fps=1, workers=1)

    assert list(tmp_path.iterdir()) == []
