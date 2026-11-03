import os
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .chart import HEIGHT, WIDTH


# x264 по умолчанию кодирует в потоках на все ядра: threads ограничивает его.
def write_video(
    path: Path, fps: int, frames: Iterable[bytes], preset: str = "slow", threads: int = 1
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Готовность ролика проверяют по наличию файла, поэтому недорисованный не должен лечь на его место.
    partial = path.with_name(f".{path.name}.partial")
    encoder = subprocess.Popen(
        [
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(fps), "-i", "-",
            "-c:v", "libx264", "-preset", preset, "-crf", "22", "-threads", str(threads),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-an", "-f", "mp4", str(partial),
        ],
        stdin=subprocess.PIPE,
    )
    assert encoder.stdin is not None
    try:
        for raw in frames:
            encoder.stdin.write(raw)
        encoder.stdin.close()
        if code := encoder.wait():
            raise subprocess.CalledProcessError(code, "ffmpeg")
        os.replace(partial, path)
    finally:
        encoder.stdin.close()
        encoder.wait()
        partial.unlink(missing_ok=True)
