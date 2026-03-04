import random
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image

from src.bot.services.battle.models import BattleFighter
from src.bot.types import KaguneType

SPRITES_DIR = Path("src/assets/sprites/battle")

SPRITE_SIZE = (200, 360)  # ширина x высота под кадр 480x480

KAGUNE_SPRITES = {
    KaguneType.UKAKU: SPRITES_DIR / "ukaku",
    KaguneType.KOUKAKU: SPRITES_DIR / "koukaku",
    KaguneType.RINKAKU: SPRITES_DIR / "rinkaku",
    KaguneType.BIKAKU: SPRITES_DIR / "bikaku",
}


@lru_cache(maxsize=32)
def load_sprite(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img.thumbnail(SPRITE_SIZE, Image.Resampling.LANCZOS)
    return img


def get_sprite(
    fighter: "BattleFighter", flip: bool = False, path: Optional[str] = None
) -> Image.Image:
    # любой файл из папки с типом кагуне

    path_to_folder = (
        path or fighter.sprite_path or str(KAGUNE_SPRITES[fighter.kagune_type])
    )
    path_to_file = random.choice(list(Path(path_to_folder).glob("*.png")))
    sprite = load_sprite(path_to_file)
    if flip:
        sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return sprite
