import re

TIKTOK = r"https?://(?:[\w-]+\.)*tiktok\.com/[^\s<>\"']+"
YOUTUBE = (
    r"https?://(?:(?:www|m)\.)?(?:youtube\.com/(?:watch\?[^\s<>\"']*v=|shorts/)|youtu\.be/)"
    r"[\w-]{11}[^\s<>\"']*"
)
LINK = re.compile(f"{TIKTOK}|{YOUTUBE}", re.IGNORECASE)
MAX_LINKS = 3


def find_links(text: str) -> list[str]:
    links = (match.rstrip(".,!?)]}»") for match in LINK.findall(text))
    return list(dict.fromkeys(links))[:MAX_LINKS]
