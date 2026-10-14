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


TIKTOK_POST = re.compile(r"tiktok\.com/.*?/(?:video|photo)/(\d+)", re.IGNORECASE)
YOUTUBE_VIDEO = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/)|youtu\.be/)([\w-]{11})", re.IGNORECASE
)


def media_key(url: str) -> str | None:
    if found := TIKTOK_POST.search(url):
        return f"tiktok:{found[1]}"
    if found := YOUTUBE_VIDEO.search(url):
        return f"youtube:{found[1]}"
    return None
