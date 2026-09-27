import keyword
import string
from collections.abc import Mapping
from pathlib import Path

import yaml

DIALOGS_DIR = Path(__file__).parent

Texts = dict[str, tuple[str, ...]]
Placeholders = Mapping[str, frozenset[str]]


class DialogFileError(Exception):
    pass


def load_texts(folder: Path = DIALOGS_DIR) -> Texts:
    texts: Texts = {}
    for path in sorted(folder.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text("utf-8"))
        except yaml.YAMLError as exc:
            raise DialogFileError(f"{path.name}: не читается как YAML\n{exc}") from exc
        if not isinstance(data, dict):
            raise DialogFileError(f"{path.name}: ожидались фразы вида «ключ: текст»")
        _collect(data, (), path.name, texts)

    for key in texts:
        if any(other.startswith(f"{key}.") for other in texts):
            raise DialogFileError(f"{key}: это и фраза, и раздел с другими фразами")
    return texts


def _collect(
    node: dict[object, object], path: tuple[str, ...], file: str, texts: Texts
) -> None:
    for name, value in node.items():
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
            or name.startswith("_")
        ):
            raise DialogFileError(
                f"{file}: «{name}» не годится в имя (нужно как имя в Python)"
            )
        key = ".".join((*path, name))

        if isinstance(value, dict):
            _collect(value, (*path, name), file, texts)
            continue

        variants = [value] if isinstance(value, str) else value
        if (
            not isinstance(variants, list)
            or not variants
            or not all(isinstance(variant, str) for variant in variants)
        ):
            raise DialogFileError(
                f"{file}: {key} — нужен текст или непустой список текстов"
            )
        if key in texts:
            raise DialogFileError(f"{file}: {key} объявлена второй раз")
        texts[key] = tuple(variants)


def placeholders(key: str, variants: tuple[str, ...]) -> frozenset[str]:
    names: set[str] = set()
    for variant in variants:
        try:
            fields = [field for _, field, _, _ in string.Formatter().parse(variant)]
        except ValueError as exc:
            raise DialogFileError(f"{key}: сломаны фигурные скобки ({exc})") from exc
        for field in fields:
            if field is None:
                continue
            if not field.isidentifier():
                raise DialogFileError(
                    f"{key}: «{{{field}}}» — подстановка должна быть именем"
                )
            names.add(field)
    return frozenset(names)


def signatures(texts: Texts) -> dict[str, frozenset[str]]:
    return {key: placeholders(key, variants) for key, variants in texts.items()}


def check_against(texts: Texts, expected: Placeholders) -> None:
    problems = [f"{key}: нет текста" for key in sorted(expected.keys() - texts.keys())]
    problems += [
        f"{key}: нет в коде, перегенерируй дерево: python -m src.bot.dialogs.generate"
        for key in sorted(texts.keys() - expected.keys())
    ]
    for key in sorted(expected.keys() & texts.keys()):
        found = placeholders(key, texts[key])
        if found != expected[key]:
            problems.append(
                f"{key}: подстановки {sorted(found)}, а код передаёт {sorted(expected[key])}"
            )
    if problems:
        raise DialogFileError("Тексты не совпадают с кодом:\n" + "\n".join(problems))
