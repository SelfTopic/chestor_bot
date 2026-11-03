import io
import unicodedata
from dataclasses import dataclass
from functools import cache

from PIL import Image, ImageDraw

from .style import BACKGROUND_BOTTOM, BACKGROUND_TOP, LABEL, WHITE, accent, font, mix

WIDTH, SCALE = 960, 2
ROW, HEAD, PAD = 58, 64, 16
AVATARS = (
    (98, 132, 255),
    (168, 98, 255),
    (255, 120, 170),
    (64, 200, 160),
    (255, 186, 64),
    (90, 190, 255),
)
NAME_LEFT, NAME_GAP = 92, 16
AMOUNT_RIGHT, TARGET_RIGHT = WIDTH - 36, WIDTH - 186


@dataclass(frozen=True)
class PanelRow:
    name: str
    amount: str
    target: str | None
    target_cents: int | None
    # Если ник целиком из символов, которых нет в шрифте, на панели — username.
    username: str | None = None


@cache
def _drawable(char: str) -> bool:
    # Rubik не знает эмодзи, иероглифов и арабицы: вместо них вышли бы квадратики.
    missing = font(22 * SCALE, "Medium").getmask("￿").getbbox()
    return char.isspace() or font(22 * SCALE, "Medium").getmask(char).getbbox() != missing


def _clean(name: str) -> str:
    # NFKC переводит «декоративные» буквы (𝕮𝖍𝖊𝕾𝖙𝖔𝖗, ｆｕｌｌ) в обычные, которые шрифт знает.
    name = unicodedata.normalize("NFKC", name)
    return " ".join("".join(char for char in name if _drawable(char)).split())


def _fit(draw: ImageDraw.ImageDraw, text: str, width: float, size: int) -> str:
    face = font(size * SCALE, "Medium")
    if draw.textlength(text, font=face) <= width:
        return text
    while text and draw.textlength(text + "…", font=face) > width:
        text = text[:-1]
    return text + "…"


def bets_panel(title: str, bank: str, rows: list[PanelRow]) -> bytes:
    height = HEAD + ROW * len(rows) + PAD
    image = Image.new("RGB", (WIDTH * SCALE, height * SCALE))
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(height * SCALE):
        share = y / (height * SCALE) * 0.6
        draw.line([(0, y), (WIDTH * SCALE, y)], fill=mix(BACKGROUND_BOTTOM, BACKGROUND_TOP, share))

    middle = HEAD / 2 * SCALE
    heading = font(22 * SCALE, "Black")
    draw.text((32 * SCALE, middle), title, font=heading, fill=WHITE, anchor="lm")
    badge = 32 * SCALE + draw.textlength(title, font=heading) + 12 * SCALE
    draw.rounded_rectangle(
        [badge, middle - 14 * SCALE, badge + 40 * SCALE, middle + 14 * SCALE],
        radius=14 * SCALE,
        fill=(255, 255, 255, 28),
    )
    count = font(18 * SCALE, "Bold")
    draw.text((badge + 20 * SCALE, middle), str(len(rows)), font=count, fill=WHITE, anchor="mm")
    draw.text(
        ((WIDTH - 32) * SCALE, middle), bank, font=font(20 * SCALE, "SemiBold"), fill=LABEL, anchor="rm"
    )

    for index, row in enumerate(rows):
        _row(draw, index, row)

    buffer = io.BytesIO()
    image.resize((WIDTH, height), Image.Resampling.LANCZOS).save(buffer, "PNG")
    return buffer.getvalue()


def _row(draw: ImageDraw.ImageDraw, index: int, row: PanelRow) -> None:
    top = (HEAD + index * ROW) * SCALE
    middle = top + ROW / 2 * SCALE
    draw.rounded_rectangle(
        [16 * SCALE, top + 4 * SCALE, (WIDTH - 16) * SCALE, top + (ROW - 4) * SCALE],
        radius=14 * SCALE,
        fill=(255, 255, 255, 14 if index % 2 == 0 else 8),
    )
    name = _clean(row.name) or _clean(row.username or "") or "?"
    radius = 18 * SCALE
    color = AVATARS[sum(map(ord, name)) % len(AVATARS)]
    draw.ellipse([36 * SCALE, middle - radius, 36 * SCALE + 2 * radius, middle + radius], fill=color)
    initial = font(20 * SCALE, "Bold")
    draw.text((36 * SCALE + radius, middle), name[0].upper(), font=initial, fill=WHITE, anchor="mm")
    draw.text(
        (AMOUNT_RIGHT * SCALE, middle), row.amount, font=font(24 * SCALE, "Bold"), fill=WHITE, anchor="rm"
    )

    name_right = AMOUNT_RIGHT - 150
    if row.target is not None and row.target_cents is not None:
        pill = font(17 * SCALE, "SemiBold")
        width = draw.textlength(row.target, font=pill) + 24 * SCALE
        right = TARGET_RIGHT * SCALE
        tint = accent(row.target_cents / 100)
        draw.rounded_rectangle(
            [right - width, middle - 15 * SCALE, right, middle + 15 * SCALE],
            radius=15 * SCALE,
            fill=tint + (60,),
            outline=tint + (200,),
            width=2 * SCALE,
        )
        draw.text((right - width / 2, middle), row.target, font=pill, fill=WHITE, anchor="mm")
        name_right = (right - width) / SCALE
    room = (name_right - NAME_GAP - NAME_LEFT) * SCALE
    draw.text(
        (NAME_LEFT * SCALE, middle),
        _fit(draw, name, room, 22),
        font=font(22 * SCALE, "Medium"),
        fill=WHITE,
        anchor="lm",
    )
