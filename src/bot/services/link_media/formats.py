from dataclasses import dataclass
from typing import Any

# Версия TikTok с водяным знаком.
WATERMARKED = "download"
MAX_HEIGHT = 1080


@dataclass(frozen=True)
class Choice:
    selector: str
    size: int


def _size(fmt: dict[str, Any]) -> int | None:
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    return int(size) if isinstance(size, (int, float)) and size > 0 else None


def _has(fmt: dict[str, Any], codec: str) -> bool:
    return fmt.get(codec) not in (None, "none")


def _height(fmt: dict[str, Any]) -> int:
    height = fmt.get("height")
    return int(height) if isinstance(height, (int, float)) else 0


def _h264(fmt: dict[str, Any]) -> bool:
    return str(fmt.get("vcodec") or "").startswith(("avc", "h264"))


def has_video(info: dict[str, Any]) -> bool:
    return any(_has(fmt, "vcodec") for fmt in _formats(info))


def _formats(info: dict[str, Any]) -> list[dict[str, Any]]:
    formats = info.get("formats")
    if not isinstance(formats, list):
        return []
    return [
        fmt for fmt in formats if isinstance(fmt, dict) and fmt.get("format_id") != WATERMARKED
    ]


def pick(info: dict[str, Any], limit: int) -> Choice | None:
    formats = _formats(info)
    candidates: list[tuple[tuple[int, bool, int], Choice]] = []

    for fmt in formats:
        size = _size(fmt)
        if _has(fmt, "vcodec") and _has(fmt, "acodec") and size is not None:
            candidates.append(((_height(fmt), _h264(fmt), size), Choice(fmt["format_id"], size)))

    # В mp4 без перекодирования склеивается только звук m4a.
    audios = [
        fmt
        for fmt in formats
        if _has(fmt, "acodec") and not _has(fmt, "vcodec") and fmt.get("ext") == "m4a"
    ]
    audio = max(audios, key=lambda fmt: fmt.get("abr") or 0, default=None)
    audio_size = _size(audio) if audio is not None else None
    if audio is not None and audio_size is not None:
        for fmt in formats:
            size = _size(fmt)
            if not _has(fmt, "vcodec") or _has(fmt, "acodec") or size is None:
                continue
            if fmt.get("ext") != "mp4":
                continue
            selector = f"{fmt['format_id']}+{audio['format_id']}"
            candidates.append(((_height(fmt), _h264(fmt), size), Choice(selector, size + audio_size)))

    fitting = [
        (key, choice)
        for key, choice in candidates
        if choice.size <= limit and key[0] <= MAX_HEIGHT
    ]
    if not fitting:
        return None
    return max(fitting, key=lambda item: item[0])[1]
