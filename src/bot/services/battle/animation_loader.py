import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import av
import numpy as np
from PIL import Image

from src.bot.types import KaguneType

logger = logging.getLogger(__name__)

BASE_DIR = Path("src/assets")
ANIMATIONS_DIR = BASE_DIR / "animation" / "battle"

ATTACKER_CLIP = {
    "hit": "attack",
    "crit": "attack",
    "miss": "attack",
    "block": "attack",
    "regen": "regen",
}

DEFENDER_CLIP = {
    "hit": "idle",
    "crit": "idle",
    "miss": "miss",
    "block": "idle",
    "regen": "idle",
}


def get_animation_path(
    event_type: str,
    fighter_name: str,
    kagune_type: KaguneType,
    role: str = "attacker",
) -> Optional[str]:
    if event_type == "idle":
        base = "idle"
    else:
        table = ATTACKER_CLIP if role == "attacker" else DEFENDER_CLIP
        base = table.get(event_type)

    if base is None:
        return None

    candidate_paths = [
        ANIMATIONS_DIR / fighter_name.lower() / f"{base}.webm",
        ANIMATIONS_DIR / kagune_type.value["name_english"].lower() / f"{base}.webm",
    ]

    for path in candidate_paths:
        if path.is_file():
            return str(path)

    return None


@lru_cache(maxsize=128)
def _decode_webm_rgba(
    path: str,
    target_height: int,
) -> List[np.ndarray]:
    """Декодирует webm без flip — flip делается на лету в get_clip_frame.
    Так один файл кешируется один раз для обоих игроков."""
    frames: List[np.ndarray] = []

    try:
        container = av.open(path)
    except Exception as e:
        logger.error(f"Failed to open {path}: {e}")
        return []

    try:
        stream = container.streams.video[0]

        for frame in container.decode(stream):
            arr = frame.to_ndarray(format="rgba")

            # VP9 alpha track недоступен через PyAV — убираем чёрный фон
            if arr[:, :, 3].min() == 255:
                black = (arr[:, :, 0] < 15) & (arr[:, :, 1] < 15) & (arr[:, :, 2] < 15)
                arr[:, :, 3] = np.where(black, 0, 255)

            if arr.shape[0] != target_height:
                img = Image.fromarray(arr, "RGBA")
                ratio = target_height / img.height
                new_size = (int(img.width * ratio), target_height)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                arr = np.array(img)

            frames.append(arr)

    except Exception as e:
        logger.error(f"Error decoding {path}: {e}")
        frames = []

    finally:
        container.close()

    logger.debug(f"Decoded {len(frames)} frames from {path}")
    return frames


def get_clip_frame(
    path: Optional[str],
    progress: float,
    flip: bool = False,
    target_height: int = 220,
) -> Optional[Image.Image]:
    if not path:
        return None

    frames = _decode_webm_rgba(path, target_height)
    if not frames:
        return None

    progress = min(max(progress, 0.0), 1.0)
    idx = min(int(progress * (len(frames) - 1)), len(frames) - 1)

    arr = frames[idx]
    if flip:
        arr = np.flip(arr, axis=1)  # view, без copy — быстро

    return Image.fromarray(arr, "RGBA")
