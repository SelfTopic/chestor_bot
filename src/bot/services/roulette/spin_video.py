import io
from collections.abc import Iterator
from pathlib import Path

from PIL import Image

from src.bot.config import game_config

from ..arcade.encoder import write_video
from .positions import CENTER, POSITIONS, Spin, spin
from .ribbon import CARD_WIDTH, PITCH, RibbonPainter

# Telegram проигрывает ролики на 25 кадрах, какой бы ни была их частота.
FPS = 25
# Частота в пути: ролики с другой частотой не подхватятся вместо новых.
VIDEOS = Path(game_config.path_to_assets) / "videos" / "roulette" / f"{FPS}fps"

REST, ACCEL, DECEL, MAGNET, FLASH = 0.4, 0.7, 4.0, 0.45, 0.35
# Плашка уже горит, когда ролик доходит до этого времени: дальше он стоит на последнем кадре.
LANDED_SECONDS = REST + ACCEL + DECEL + MAGNET + FLASH
# Запас, чтобы правка с картинкой успела прийти раньше, чем гифка пойдёт по кругу.
TAIL = 2.0
BLUR_SHARE = 0.3
MIN_BLUR = 3.0


def spin_video_path(start: int, end: int) -> Path:
    return VIDEOS / f"{start}-{end}.mp4"


def _ease_out(share: float) -> float:
    return 1 - (1 - share) ** 3


def _smoothstep(share: float) -> float:
    return share * share * (3 - 2 * share)


class SpinFrames:
    def __init__(self, spin: Spin, fps: int = FPS, painter: RibbonPainter | None = None) -> None:
        self.spin = spin
        self.fps = fps
        self.painter = painter or RibbonPainter()
        self.start = spin.start_card * PITCH
        self.target = spin.end_card * PITCH
        self.stop = self.target + spin.miss * CARD_WIDTH
        self.length = self.stop - self.start
        # Разгон с постоянным ускорением, на стыке торможение начинается с той же скорости.
        self.top_speed = self.length / (ACCEL / 2 + DECEL / 3)

    @property
    def count(self) -> int:
        return round((LANDED_SECONDS + TAIL) * self.fps)

    def frames(self) -> Iterator[bytes]:
        for index in range(self.count):
            yield self.render(index).tobytes()

    def render(self, index: int) -> Image.Image:
        clock = index / self.fps
        cards = self.spin.cards
        if clock < REST:
            fading = 1 - min(clock / FLASH, 1.0)
            return self.painter.frame(cards, self.start, lit=fading, lit_card=self.spin.start_card)
        clock -= REST
        if clock < ACCEL + DECEL:
            offset, speed = self._travel(clock)
            blur = speed / self.fps * BLUR_SHARE
            return self.painter.frame(cards, offset, blur=blur if blur >= MIN_BLUR else 0.0)
        clock -= ACCEL + DECEL
        if clock < MAGNET:
            offset = self.stop + (self.target - self.stop) * _smoothstep(clock / MAGNET)
            return self.painter.frame(cards, offset)
        clock -= MAGNET
        lit = min(clock / FLASH, 1.0)
        return self.painter.frame(cards, self.target, lit=lit, lit_card=self.spin.end_card)

    def _travel(self, clock: float) -> tuple[float, float]:
        if clock < ACCEL:
            return (
                self.start + self.top_speed * clock * clock / (2 * ACCEL),
                self.top_speed * clock / ACCEL,
            )
        share = (clock - ACCEL) / DECEL
        accelerated = self.top_speed * ACCEL / 2
        remaining = self.length - accelerated
        return (
            self.start + accelerated + remaining * _ease_out(share),
            remaining * 3 * (1 - share) ** 2 / DECEL,
        )


def rest_frame(position: int, painter: RibbonPainter | None = None) -> Image.Image:
    painter = painter or RibbonPainter()
    return painter.frame(POSITIONS[position], CENTER * PITCH, lit=1.0, lit_card=CENTER)


def rest_picture(position: int) -> bytes:
    buffer = io.BytesIO()
    rest_frame(position).save(buffer, "PNG")
    return buffer.getvalue()


def render_spin_video(start: int, end: int, path: Path | None = None) -> Path:
    path = path or spin_video_path(start, end)
    write_video(path, FPS, SpinFrames(spin(start, end)).frames(), preset="medium")
    return path
