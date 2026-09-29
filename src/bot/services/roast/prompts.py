from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


class RoastPrompts:
    def __init__(self, folder: Path = PROMPTS_DIR) -> None:
        self._folder = folder
        self._cache: dict[str, tuple[float, str]] = {}

    @property
    def persona(self) -> str:
        return self._read("persona.md")

    @property
    def request(self) -> str:
        return self._read("request.md")

    def examples(self) -> list[str]:
        return self._lines("examples.txt")

    def insults(self) -> list[str]:
        return self._lines("insults.txt")

    def _lines(self, name: str) -> list[str]:
        return [
            line.strip()
            for line in self._read(name).splitlines()
            if line.strip() and not line.startswith("#")
        ]

    # Файлы перечитываются при изменении: инструкцию правят на ходу, без перезапуска бота.
    def _read(self, name: str) -> str:
        path = self._folder / name
        mtime = path.stat().st_mtime
        cached = self._cache.get(name)
        if cached is None or cached[0] != mtime:
            cached = (mtime, path.read_text("utf-8").strip())
            self._cache[name] = cached
        return cached[1]
