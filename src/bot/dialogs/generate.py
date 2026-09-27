from dataclasses import dataclass, field
from pathlib import Path

from .texts import load_texts, signatures

TREE_PATH = Path(__file__).with_name("tree.py")

HEADER = """# Сгенерировано из src/bot/dialogs/*.yaml: python -m src.bot.dialogs.generate
# Руками не править: тест сверяет файл с YAML.
from .line import Line
"""


@dataclass
class _Node:
    path: tuple[str, ...]
    phrases: dict[str, frozenset[str]] = field(default_factory=dict)
    sections: dict[str, "_Node"] = field(default_factory=dict)

    @property
    def class_name(self) -> str:
        words = (word for part in self.path for word in part.split("_"))
        return "_" + "".join(word[:1].upper() + word[1:] for word in words) + "Dialogs"


def _tree(placeholders: dict[str, frozenset[str]]) -> _Node:
    root = _Node(())
    for key, names in placeholders.items():
        *sections, phrase = key.split(".")
        node = root
        for section in sections:
            node = node.sections.setdefault(section, _Node((*node.path, section)))
        node.phrases[phrase] = names
    return root


def _method(key: str, phrase: str, names: frozenset[str]) -> list[str]:
    ordered = sorted(names)
    params = ", ".join(f"{name}: object" for name in ordered)
    signature = (
        f"    def {phrase}(self, *, {params}) -> Line:"
        if ordered
        else f"    def {phrase}(self) -> Line:"
    )
    if len(signature) > 88:
        signature_lines = [f"    def {phrase}(", "        self,", "        *,"]
        signature_lines += [f"        {name}: object," for name in ordered]
        signature_lines.append("    ) -> Line:")
    else:
        signature_lines = [signature]

    params_dict = ", ".join(f'"{name}": {name}' for name in ordered)
    call = f'        return Line("{key}", {{{params_dict}}})'
    if len(call) > 88:
        call_lines = ["        return Line(", f'            "{key}",', "            {"]
        call_lines += [f'                "{name}": {name},' for name in ordered]
        call_lines += ["            },", "        )"]
    else:
        call_lines = [call]
    return signature_lines + call_lines


def _classes(node: _Node, out: list[str]) -> None:
    for section in sorted(node.sections):
        _classes(node.sections[section], out)

    body: list[str] = []
    for section in sorted(node.sections):
        body.append(f"    {section} = {node.sections[section].class_name}()")
    for phrase in sorted(node.phrases):
        if body:
            body.append("")
        body += _method(".".join((*node.path, phrase)), phrase, node.phrases[phrase])

    out += ["", "", f"class {node.class_name}:", *body]


def render_tree(placeholders: dict[str, frozenset[str]]) -> str:
    root = _tree(placeholders)
    out = [HEADER.rstrip("\n")]
    _classes(root, out)
    classes = [line for line in out if line.startswith("class ")]
    # «eat_human» и «eatHuman» дали бы один класс: второй молча затёр бы первый.
    assert len(classes) == len(set(classes)), "два раздела получили одно имя класса"

    out += ["", "", f"Dialogs = {root.class_name}()", ""]
    out.append("PLACEHOLDERS: dict[str, frozenset[str]] = {")
    for key in sorted(placeholders):
        quoted = ", ".join(f'"{name}"' for name in sorted(placeholders[key]))
        entry = (
            f'    "{key}": frozenset({{{quoted}}}),'
            if quoted
            else f'    "{key}": frozenset(),'
        )
        if len(entry) > 88:
            out.append(f'    "{key}": frozenset(')
            out.append("        {")
            out += [f'            "{name}",' for name in sorted(placeholders[key])]
            out += ["        }", "    ),"]
        else:
            out.append(entry)
    out.append("}")
    return "\n".join(out) + "\n"


def main() -> None:
    TREE_PATH.write_text(render_tree(signatures(load_texts())), "utf-8")
    print(f"Записано: {TREE_PATH}")


if __name__ == "__main__":
    main()
