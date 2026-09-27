import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


class VideoCutterService:
    PATH_TO_CUTTED = Path("src/assets/videos/cutter")

    def __init__(self) -> None:
        self.PATH_TO_CUTTED.mkdir(exist_ok=True, parents=True)
        # Одно ядро оставляем event loop'у: ffmpeg на всех ядрах вешает бота.
        self._encode_threads = max(1, (os.cpu_count() or 2) - 1)

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        pattern = r"^\d{1,2}:\d{2}$"
        if not re.match(pattern, time_str):
            return False
        minutes, seconds = map(int, time_str.split(":"))
        return seconds < 60

    def parse_duration(self, start_time: str, end_time: str) -> int:
        if not self.validate_time_format(start_time):
            raise ValueError("Invalid start time format. Use MM:SS.")
        if not self.validate_time_format(end_time):
            raise ValueError("Invalid end time format. Use MM:SS.")

        start_minutes, start_seconds = map(int, start_time.split(":"))
        end_minutes, end_seconds = map(int, end_time.split(":"))

        start_total = start_minutes * 60 + start_seconds
        end_total = end_minutes * 60 + end_seconds
        duration = end_total - start_total

        if duration <= 0:
            raise ValueError("End time must be greater than start time.")

        return duration

    def generate_output_path(
        self, input_filename: str | Path, is_gif: bool = False
    ) -> Path:
        kind = "gif" if is_gif else "video"
        return (
            self.PATH_TO_CUTTED
            / f"{Path(input_filename).stem}_{kind}_{uuid.uuid4()}.mp4"
        )

    async def cut_video_async(
        self,
        input_file_path: str | Path,
        output_file_path: str | Path,
        start_time: str,
        end_time: str,
        as_animation: bool = False,
    ) -> Path:
        logger.info(
            f"Starting async video cut: {input_file_path} -> {output_file_path}"
        )

        duration = self.parse_duration(start_time, end_time)
        options: dict[str, object] = {"t": duration, "threads": self._encode_threads}
        if as_animation:
            # Telegram хранит «гифки» как MP4 без звука; настоящий GIF ограничен 256 цветами
            # на кадр и выходит мыльным, а H.264 сохраняет исходное качество.
            options |= {
                "an": None,
                "vcodec": "libx264",
                "preset": "veryfast",
                "crf": 18,
                "pix_fmt": "yuv420p",
                "movflags": "+faststart",
            }
        else:
            options["preset"] = "ultrafast"

        cmd = (
            ffmpeg.input(str(input_file_path), ss=start_time)
            .output(str(output_file_path), **options)
            .overwrite_output()
            .compile()
        )

        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"FFmpeg failed: {error_msg}")
                raise RuntimeError(f"FFmpeg error: {error_msg}")

            logger.info(f"Video cut completed: {output_file_path}")
            return Path(output_file_path)

        except Exception as e:
            logger.error(f"Error during video cut: {e}")
            if Path(output_file_path).exists():
                Path(output_file_path).unlink(missing_ok=True)
            raise
