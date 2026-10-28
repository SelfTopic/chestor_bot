import logging
import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from src.bot.config import game_config
from src.bot.dialogs import (
    BASE_LANGUAGE,
    DIALOGS_DIR,
    FALLBACK_LANGUAGE,
    PLACEHOLDERS,
    DialogFileError,
    Line,
    LineText,
    Phrase,
    Phrases,
    Placeholders,
    check_against,
    check_translation,
    load_texts,
    load_translations,
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
        on_broken: Callable[[Exception], None] | None = None,
    ) -> None:
        self._folder = folder
        self._on_broken = on_broken
        self._expected = expected
        self._animation_root = animation_root
        self._random = random.Random()
        self._stamp = self._files_stamp()
        self._phrases, self._translations = self._load()

    def text(self, line: Line, language: str = BASE_LANGUAGE) -> str:
        variants = self._variants(line.key, language)
        # Подстановка-фраза раскрывается в свой текст: иначе в сообщение ушёл бы repr Line.
        params = {
            name: self.text(value, language) if isinstance(value, Line) else value
            for name, value in line.params.items()
        }
        return self._random.choice(variants).format_map(params)

    def text_in(self, language: str) -> LineText:
        return partial(self.text, language=language)

    def gifs(self, line: Line) -> Gifs:
        phrase = self._phrase(line)
        # Корень читается при каждом вызове, как в media_paths: путь к ассетам настраивается.
        root = self._animation_root or Path(game_config.path_to_assets) / "animation"
        # Папки гифок общие для всех языков и названы по-русски: upgrade_kagune/Укаку.
        params = {
            name: self.text(value) if isinstance(value, Line) else value
            for name, value in line.params.items()
        }
        folder = root / phrase.gifs.format_map(params)
        # Значение подстановки могло бы увести путь из папки анимаций («..», «/»).
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"{line.key}: папка гифок {folder} вне {root}")
        last = re.fullmatch(r"\{(\w+)\}", phrase.gifs.rsplit("/", 1)[-1])
        return Gifs(folder, phrase.gif_chance, last.group(1) if last else None)

    def languages(self) -> tuple[str, ...]:
        self._reload_if_changed()
        return (BASE_LANGUAGE, *self._translations)

    def language_for(self, telegram_code: str | None) -> str:
        # Telegram присылает и региональные коды: pt-br, zh-hans.
        language = (telegram_code or "").split("-")[0].lower()
        return language if language in self.languages() else FALLBACK_LANGUAGE

    def has_phrase(self, key: str) -> bool:
        self._reload_if_changed()
        return key in self._phrases

    def keys(self) -> list[str]:
        self._reload_if_changed()
        return sorted(self._phrases)

    def _phrase(self, line: Line) -> Phrase:
        self._reload_if_changed()
        return self._phrases[line.key]

    def _variants(self, key: str, language: str) -> tuple[str, ...]:
        self._reload_if_changed()
        if language != BASE_LANGUAGE:
            for candidate in (language, FALLBACK_LANGUAGE):
                phrase = self._translations.get(candidate, {}).get(key)
                if phrase is not None:
                    return phrase.variants
        return self._phrases[key].variants

    def _files_stamp(self) -> tuple[tuple[str, float], ...]:
        paths = [*self._folder.glob("*.yaml"), *self._folder.glob("*/*.yaml")]
        return tuple(
            (str(path.relative_to(self._folder)), path.stat().st_mtime)
            for path in sorted(paths)
        )

    def _load(self) -> tuple[Phrases, dict[str, Phrases]]:
        phrases = load_texts(self._folder)
        check_against(phrases, self._expected)
        translations = load_translations(self._folder)
        for language, translation in translations.items():
            check_translation(language, translation, phrases)
        return phrases, translations

    def _reload_if_changed(self) -> None:
        stamp = self._files_stamp()
        if stamp == self._stamp:
            return
        # Новый снимок запоминается и при ошибке: иначе предупреждение шло бы на каждый ответ.
        self._stamp = stamp
        try:
            self._phrases, self._translations = self._load()
        except (DialogFileError, OSError) as exc:
            logger.warning("Тексты не перечитаны, бот отвечает прежними", exc_info=True)
            if self._on_broken is not None:
                self._on_broken(exc)
            return
        logger.info(f"Тексты перечитаны из {self._folder}: {len(self._phrases)} фраз")


__all__ = ["DialogService"]
