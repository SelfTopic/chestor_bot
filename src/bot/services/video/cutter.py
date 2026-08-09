import asyncio
import logging
import re
import uuid
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


class VideoCutterService:
    PATH_TO_CUTTED = "src/assets/videos/cutter"

    def parse_duration(
        self,
        start_time: str,
        end_time: str,
    ) -> int:
        logger.info("Parsing duration for video cut job.")
        if not self.validate_time_format(start_time):
            raise ValueError("Invalid start time format. Use MM:SS.")

        if not self.validate_time_format(end_time):
            raise ValueError("Invalid end time format. Use MM:SS.")

        start_minutes, start_seconds = map(
            int,
            start_time.split(":"),
        )

        end_minutes, end_seconds = map(
            int,
            end_time.split(":"),
        )

        start_seconds_total = start_minutes * 60 + start_seconds

        end_seconds_total = end_minutes * 60 + end_seconds

        duration = end_seconds_total - start_seconds_total

        if duration <= 0:
            raise ValueError("End time must be greater than start time.")

        return duration

    def generate_output_path(self, input_filename: str | Path):
        return Path(self.PATH_TO_CUTTED) / (
            Path(input_filename).stem + str(uuid.uuid4()) + ".mp4"
        )

    @staticmethod
    def validate_time_format(
        time_str: str,
    ) -> bool:
        pattern = r"^\d{1,2}:\d{2}$"

        if not re.match(pattern, time_str):
            logger.error("Invalid time format: %s. Expected MM:SS.", time_str)
            return False

        minutes, seconds = map(
            int,
            time_str.split(":"),
        )

        return seconds < 60

    def _cut_video(
        self,
        input_file_path: str,
        output_file_path: str,
        start_time: str,
        duration: int,
    ) -> None:
        (
            ffmpeg.input(
                input_file_path,
                ss=start_time,
            )
            .output(output_file_path, t=duration, vcodec="copy", acodec="copy")
            .overwrite_output()
            .run(quiet=True)
        )

    async def cut_video(
        self,
        input_file_path: str,
        output_file_path: str,
        start_time: str,
        end_time: str,
    ) -> str:
        logger.info("Starting video cut job: %s", output_file_path)
        duration = self.parse_duration(
            start_time,
            end_time,
        )

        await asyncio.to_thread(
            self._cut_video,
            input_file_path,
            output_file_path,
            start_time,
            duration,
        )
        logger.info("Finished video cut job: %s", output_file_path)

        return output_file_path
