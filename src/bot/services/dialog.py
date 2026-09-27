import logging
import random
import re
from dataclasses import dataclass
from pathlib import Path

from src.bot.config import game_config
from src.bot.dialogs import (
    DIALOGS_DIR,
    PLACEHOLDERS,
    DialogFileError,
    Line,
    Phrase,
    Placeholders,
    check_against,
    load_texts,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Gifs:
    folder: Path
    chance: float
    # Подстановка, которая целиком задаёт последнюю папку (upgrade_kagune/{kagune}).
    varying: str | None = None


class DialogService:
    def __init__(
        self,
        folder: Path = DIALOGS_DIR,
        expected: Placeholders = PLACEHOLDERS,
        animation_root: Path | None = None,
    ) -> None:
        self._folder = folder
        self._expected = expected
        self._animation_root = animation_root
        self._random = random.Random()
        self._stamp = self._files_stamp()
        self._phrases = self._load()

    def text(self, line: Line) -> str:
        variants = self._phrase(line).variants
        return self._random.choice(variants).format_map(line.params)

    def gifs(self, line: Line) -> Gifs:
        phrase = self._phrase(line)
        # Корень читается при каждом вызове, как в media_paths: путь к ассетам настраивается.
        root = self._animation_root or Path(game_config.path_to_assets) / "animation"
        folder = root / phrase.gifs.format_map(line.params)
        # Значение подстановки могло бы увести путь из папки анимаций («..», «/»).
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"{line.key}: папка гифок {folder} вне {root}")
        last = re.fullmatch(r"\{(\w+)\}", phrase.gifs.rsplit("/", 1)[-1])
        return Gifs(folder, phrase.gif_chance, last.group(1) if last else None)

    def has_phrase(self, key: str) -> bool:
        self._reload_if_changed()
        return key in self._phrases

    def keys(self) -> list[str]:
        self._reload_if_changed()
        return sorted(self._phrases)

    def _phrase(self, line: Line) -> Phrase:
        self._reload_if_changed()
        return self._phrases[line.key]

    def _files_stamp(self) -> tuple[tuple[str, float], ...]:
        return tuple(
            (path.name, path.stat().st_mtime)
            for path in sorted(self._folder.glob("*.yaml"))
        )

    def _load(self) -> dict[str, Phrase]:
        phrases = load_texts(self._folder)
        check_against(phrases, self._expected)
        return phrases

    def _reload_if_changed(self) -> None:
        stamp = self._files_stamp()
        if stamp == self._stamp:
            return
        # Новый снимок запоминается и при ошибке: иначе предупреждение шло бы на каждый ответ.
        self._stamp = stamp
        try:
            self._phrases = self._load()
        except (DialogFileError, OSError):
            logger.warning("Тексты не перечитаны, бот отвечает прежними", exc_info=True)
            return
        logger.info(f"Тексты перечитаны из {self._folder}: {len(self._phrases)} фраз")


__all__ = ["DialogService"]
