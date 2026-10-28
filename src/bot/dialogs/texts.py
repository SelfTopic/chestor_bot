import keyword
import string
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

DIALOGS_DIR = Path(__file__).parent

BASE_LANGUAGE = "ru"
# Чего нет в переводе, бот говорит по-английски: иранцу или арабу он понятнее русского.
FALLBACK_LANGUAGE = "en"

# Разбор через libyaml на порядок быстрее; без неё — тот же разбор на Python.
SafeLoader: type[yaml.SafeLoader] = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

PHRASE_FIELDS = frozenset({"text", "gifs", "gif_chance"})

Placeholders = Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class Phrase:
    variants: tuple[str, ...]
    gifs: str
    gif_chance: float


Phrases = dict[str, Phrase]


class DialogFileError(Exception):
    pass


def load_texts(folder: Path = DIALOGS_DIR) -> Phrases:
    phrases: Phrases = {}
    for path in sorted(folder.glob("*.yaml")):
        try:
            data = yaml.load(path.read_text("utf-8"), Loader=SafeLoader)
        except yaml.YAMLError as exc:
            raise DialogFileError(f"{path.name}: не читается как YAML\n{exc}") from exc
        if not isinstance(data, dict):
            raise DialogFileError(f"{path.name}: ожидались фразы вида «ключ: текст»")
        _collect(data, (), path.name, phrases)

    for key in phrases:
        if any(other.startswith(f"{key}.") for other in phrases):
            raise DialogFileError(f"{key}: это и фраза, и раздел с другими фразами")
    return phrases


def load_translations(folder: Path = DIALOGS_DIR) -> dict[str, Phrases]:
    return {
        path.name: load_texts(path)
        for path in sorted(folder.iterdir())
        if path.is_dir() and any(path.glob("*.yaml"))
    }


def _collect(
    node: dict[object, object], path: tuple[str, ...], file: str, phrases: Phrases
) -> None:
    for name, value in node.items():
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
            or name.startswith("_")
            or name in PHRASE_FIELDS
        ):
            raise DialogFileError(
                f"{file}: «{name}» не годится в имя (нужно как имя в Python, "
                f"и не {', '.join(sorted(PHRASE_FIELDS))})"
            )
        key = ".".join((*path, name))

        if isinstance(value, dict) and "text" not in value:
            _collect(value, (*path, name), file, phrases)
            continue

        if key in phrases:
            raise DialogFileError(f"{file}: {key} объявлена второй раз")
        phrases[key] = _phrase(key, value, file)


def _phrase(key: str, value: object, file: str) -> Phrase:
    fields: dict[object, object] = value if isinstance(value, dict) else {"text": value}
    unknown = set(fields) - PHRASE_FIELDS
    if unknown:
        raise DialogFileError(
            f"{file}: {key} — непонятные поля {sorted(map(str, unknown))}"
        )

    text = fields["text"]
    variants = [text] if isinstance(text, str) else text
    if (
        not isinstance(variants, list)
        or not variants
        or not all(isinstance(variant, str) for variant in variants)
    ):
        raise DialogFileError(
            f"{file}: {key} — нужен текст или непустой список текстов"
        )

    gifs = fields.get("gifs", key)
    if not isinstance(gifs, str) or not gifs or ".." in Path(gifs).parts:
        raise DialogFileError(
            f"{file}: {key} — gifs должен быть папкой внутри animation"
        )

    chance = fields.get("gif_chance", 1)
    if (
        isinstance(chance, bool)
        or not isinstance(chance, (int, float))
        or not 0 <= chance <= 1
    ):
        raise DialogFileError(
            f"{file}: {key} — gif_chance должен быть числом от 0 до 1"
        )

    return Phrase(tuple(variants), gifs, float(chance))


def _fields(key: str, template: str) -> set[str]:
    try:
        fields = [field for _, field, _, _ in string.Formatter().parse(template)]
    except ValueError as exc:
        raise DialogFileError(f"{key}: сломаны фигурные скобки ({exc})") from exc
    names: set[str] = set()
    for field in fields:
        if field is None:
            continue
        if not field.isidentifier():
            raise DialogFileError(
                f"{key}: «{{{field}}}» — подстановка должна быть именем"
            )
        names.add(field)
    return names


def _text_placeholders(key: str, phrase: Phrase) -> set[str]:
    names: set[str] = set()
    for variant in phrase.variants:
        names |= _fields(key, variant)
    return names


def placeholders(key: str, phrase: Phrase) -> frozenset[str]:
    return frozenset(_fields(key, phrase.gifs) | _text_placeholders(key, phrase))


def signatures(phrases: Phrases) -> dict[str, frozenset[str]]:
    return {key: placeholders(key, phrase) for key, phrase in phrases.items()}


def check_against(phrases: Phrases, expected: Placeholders) -> None:
    problems = [
        f"{key}: нет текста" for key in sorted(expected.keys() - phrases.keys())
    ]
    problems += [
        f"{key}: нет в коде, перегенерируй дерево: python -m src.bot.dialogs.generate"
        for key in sorted(phrases.keys() - expected.keys())
    ]
    for key in sorted(expected.keys() & phrases.keys()):
        found = placeholders(key, phrases[key])
        if found != expected[key]:
            problems.append(
                f"{key}: подстановки {sorted(found)}, а код передаёт {sorted(expected[key])}"
            )
    if problems:
        raise DialogFileError("Тексты не совпадают с кодом:\n" + "\n".join(problems))


# Гифки у фразы общие для всех языков, поэтому сверяется только текст.
def check_translation(language: str, translation: Phrases, base: Phrases) -> None:
    problems = [
        f"{language}/{key}: такой фразы нет в русских текстах"
        for key in sorted(translation.keys() - base.keys())
    ]
    for key in sorted(translation.keys() & base.keys()):
        found = _text_placeholders(key, translation[key])
        expected = _text_placeholders(key, base[key])
        if found != expected:
            problems.append(
                f"{language}/{key}: подстановки {sorted(found)}, а в русском {sorted(expected)}"
            )
    if problems:
        raise DialogFileError(
            f"Перевод {language} не совпадает с русским:\n" + "\n".join(problems)
        )
