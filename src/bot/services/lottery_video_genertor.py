import logging
import os
import random
import uuid
from pathlib import Path

import numpy as np
from moviepy import VideoClip, concatenate_videoclips
from PIL import Image, ImageDraw

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class LotteryGenerator:
    colors: dict = {
        "red": (220, 50, 50),
        "green": (50, 200, 80),
        "blue": (50, 120, 220),
        "yellow": (230, 200, 30),
        "white": (230, 230, 230),
    }

    def __init__(
        self,
        output_dir: str | Path = "videos",
        videos_per_color: int = 10,
        video_size: tuple = (480, 480),
        fps: int = 30,
        spin_duration: float = 5.0,
        pause_duration: float = 2.0,
        circle_radius: int = 50,
        circle_spacing: int = 140,
        deceleration_start: float = 0.5,
    ):
        self.output_dir = output_dir
        self.videos_per_color = videos_per_color
        self.video_w, self.video_h = video_size
        self.fps = fps
        self.spin_duration = spin_duration
        self.pause_duration = pause_duration
        self.circle_radius = circle_radius
        self.circle_spacing = circle_spacing
        self.deceleration_start = deceleration_start
        self.strip_y = self.video_h // 2
        self.arrow_color = (255, 255, 255)
        self.arrow_size = 30

    def _ease_out_cubic(self, t: float) -> float:
        return 1 - (1 - t) ** 3

    def _slot_color(
        self, slot_index: int, winner_slot: int, winner_color: str, seed: int
    ) -> str:
        if slot_index == winner_slot:
            return winner_color
        rng = random.Random(seed ^ (slot_index * 2654435761 & 0xFFFFFFFF))
        return rng.choice(list(self.colors.keys()))

    def _compute_scroll(self, t: float, total_scroll: float) -> float:
        norm = min(t / self.spin_duration, 1.0)
        scroll_phase1 = total_scroll * 0.45
        scroll_phase2 = total_scroll - scroll_phase1
        if norm <= self.deceleration_start:
            return scroll_phase1 * (norm / self.deceleration_start)
        local = (norm - self.deceleration_start) / (1 - self.deceleration_start)
        return scroll_phase1 + scroll_phase2 * self._ease_out_cubic(local)

    def _draw_arrow(self, draw: ImageDraw.ImageDraw, cx: int, y_tip: int):
        stem_top = y_tip + self.arrow_size
        stem_bottom = y_tip + self.arrow_size * 2 + 10
        draw.line([(cx, stem_top), (cx, stem_bottom)], fill=self.arrow_color, width=4)
        draw.line(
            [(cx, y_tip), (cx - self.arrow_size, stem_top)],
            fill=self.arrow_color,
            width=4,
        )
        draw.line(
            [(cx, y_tip), (cx + self.arrow_size, stem_top)],
            fill=self.arrow_color,
            width=4,
        )

    def _draw_circle(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple):
        r = self.circle_radius
        draw.ellipse(
            [cx - r + 4, cy - r + 4, cx + r + 4, cy + r + 4], fill=(20, 20, 20)
        )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        br = max(r // 4, 5)
        bx, by = cx - r // 3, cy - r // 3
        lighter = tuple(min(255, c + 80) for c in color)
        draw.ellipse([bx - br, by - br // 2, bx + br, by + br // 2], fill=lighter)

    def _make_frame(
        self, scroll: float, winner_slot: int, winner_color: str, seed: int
    ) -> np.ndarray:
        img = Image.new("RGB", (self.video_w, self.video_h), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        center_x = self.video_w // 2
        pad = self.circle_radius + 30

        slot_left = int((scroll - center_x - pad) / self.circle_spacing) - 1
        slot_right = int((scroll + center_x + pad) / self.circle_spacing) + 1

        for i in range(slot_left, slot_right + 1):
            cx = int(center_x + i * self.circle_spacing - scroll)
            if cx < -pad or cx > self.video_w + pad:
                continue
            color_name = self._slot_color(i, winner_slot, winner_color, seed)
            color_rgb = self.colors[color_name]
            dist = abs(cx - center_x)
            max_dist = self.video_w // 2 + self.circle_radius
            alpha = max(0.3, 1.0 - dist / max_dist * 0.7)
            faded = tuple(int(c * alpha) for c in color_rgb)
            self._draw_circle(draw, cx, self.strip_y, faded)

        win_half = self.circle_radius + 15
        lc = (180, 180, 180)
        draw.line(
            [
                (center_x - win_half, self.strip_y - self.circle_radius - 20),
                (center_x - win_half, self.strip_y + self.circle_radius + 20),
            ],
            fill=lc,
            width=2,
        )
        draw.line(
            [
                (center_x + win_half, self.strip_y - self.circle_radius - 20),
                (center_x + win_half, self.strip_y + self.circle_radius + 20),
            ],
            fill=lc,
            width=2,
        )

        self._draw_arrow(draw, center_x, self.strip_y + self.circle_radius + 25)
        return np.array(img)

    def generate_video(self, winner_color: str, output_path: str | Path):
        """Рендерит один ролик и АТОМАРНО кладёт его в `output_path` - пишет
        во временный файл РЯДОМ (та же папка → та же ФС → `os.replace`
        гарантированно атомарен на POSIX) и только потом переименовывает.
        Без этого ротация (`rotate_all`, гоняется отдельным процессом
        параллельно с ботом, см. `rotate_lottery_videos.py`) могла бы
        перезаписать файл ровно в момент, когда бот его читает для отправки
        игроку - `moviepy`/`ffmpeg` сами по себе temp-file+rename не делают,
        пишут прямо в целевой путь."""

        output_path = Path(output_path)
        # Суффикс ДОЛЖЕН остаться ".mp4" - moviepy/ffmpeg определяют
        # контейнер/кодек по расширению файла, а не содержимому; с любым
        # другим хвостом (например ".mp4.tmp-...") запись молча уходит в
        # никуда - файл не создаётся вообще, без исключения (проверено).
        tmp_path = output_path.with_name(f".{output_path.stem}.tmp-{uuid.uuid4().hex}.mp4")

        seed = random.randint(0, 2**31)
        start_scroll = random.randint(50, 200) * self.circle_spacing
        extra_slots = random.randint(15, 30)
        jitter = random.uniform(-0.3, 0.3)
        winner_slot = round((start_scroll / self.circle_spacing) + extra_slots + jitter)
        final_scroll = winner_slot * self.circle_spacing
        total_scroll = final_scroll - start_scroll

        logger.debug(
            "Params: seed=%d winner_slot=%d total_scroll=%.1f",
            seed,
            winner_slot,
            total_scroll,
        )

        def spin_frame(t):
            s = start_scroll + self._compute_scroll(t, total_scroll)
            return self._make_frame(s, winner_slot, winner_color, seed)

        spin_clip = VideoClip(spin_frame, duration=self.spin_duration)
        winner_frame = self._make_frame(final_scroll, winner_slot, winner_color, seed)
        pause_clip = VideoClip(lambda _: winner_frame, duration=self.pause_duration)
        full_clip = concatenate_videoclips([spin_clip, pause_clip])

        try:
            full_clip.write_videofile(
                str(tmp_path),
                fps=self.fps,
                codec="libx264",
                audio=False,
                logger=None,
                ffmpeg_params=["-crf", "28", "-preset", "fast"],
            )
            os.replace(tmp_path, output_path)
            logger.debug("Saved: %s", output_path)
        finally:
            spin_clip.close()
            pause_clip.close()
            full_clip.close()
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def get_random_video(self, winner_color: str) -> str:
        folder = os.path.join(self.output_dir, winner_color)
        videos = [f for f in os.listdir(folder) if f.endswith(".mp4")]
        if not videos:
            logger.error("No videos found for color '%s' in '%s'", winner_color, folder)
            raise FileNotFoundError(f"No videos for color '{winner_color}'")
        chosen = random.choice(videos)
        logger.debug("Selected video: %s", chosen)
        return os.path.join(folder, chosen)

    def generate_all(self):
        os.makedirs(self.output_dir, exist_ok=True)
        total = len(self.colors) * self.videos_per_color
        done = 0

        logger.info(
            "Starting generation: %d colors × %d videos = %d total",
            len(self.colors),
            self.videos_per_color,
            total,
        )

        for color_name in self.colors:
            color_dir = os.path.join(self.output_dir, color_name)
            os.makedirs(color_dir, exist_ok=True)

            for idx in range(1, self.videos_per_color + 1):
                filename = f"{color_name}_{idx:03d}.mp4"
                output_path = os.path.join(color_dir, filename)

                if os.path.exists(output_path):
                    logger.debug("Skipping %s, already exists", filename)
                    done += 1
                    continue

                logger.info("[%d/%d] Generating %s ...", done + 1, total, filename)
                self.generate_video(color_name, output_path)
                done += 1

        logger.info("Finished! %d videos saved to '%s/'", done, self.output_dir)

    def rotate_all(self, replace_count: int = 2) -> int:
        """Гоняется периодически (см. `rotate_lottery_videos.py`),
        ОТДЕЛЬНЫМ процессом параллельно с ботом - рендер синхронный
        (`moviepy`/`ffmpeg`), внутри самого бота это заморозило бы event
        loop на реальные секунды (тот же класс бага, что уже чинили с
        нарезкой видео в `anime_router` - см. чат).

        Сначала дозаполняет пул до `videos_per_color` на цвет (первый
        запуск / пул увеличили руками), затем заменяет `replace_count`
        САМЫХ СТАРЫХ (по mtime) роликов на цвет свежими - пул медленно, но
        непрерывно обновляется, не разрастаясь на диске бесконечно.
        `generate_video` сам пишет атомарно (temp-файл + `os.replace`),
        поэтому подмена безопасна, даже если в этот момент бот как раз
        читает один из старых файлов для отправки игроку.

        Returns:
            int: сколько роликов реально было заменено (без учёта
            дозаполнения недостающих слотов).
        """

        os.makedirs(self.output_dir, exist_ok=True)
        replaced = 0

        for color_name in self.colors:
            color_dir = os.path.join(self.output_dir, color_name)
            os.makedirs(color_dir, exist_ok=True)

            for idx in range(1, self.videos_per_color + 1):
                filename = f"{color_name}_{idx:03d}.mp4"
                output_path = os.path.join(color_dir, filename)
                if not os.path.exists(output_path):
                    logger.info("Filling missing slot %s ...", filename)
                    self.generate_video(color_name, output_path)

            current_files = [
                os.path.join(color_dir, f)
                for f in os.listdir(color_dir)
                if f.endswith(".mp4")
            ]
            current_files.sort(key=os.path.getmtime)

            for path in current_files[:replace_count]:
                logger.info("Rotating %s ...", path)
                self.generate_video(color_name, path)
                replaced += 1

        logger.info("Rotation done: %d video(s) replaced.", replaced)
        return replaced
