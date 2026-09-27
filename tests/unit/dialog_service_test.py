"""Тексты в src/bot/dialogs/*.yaml и дерево Dialogs в коде (tree.py генерируется из YAML).

Код видит фразы только через дерево, поэтому расхождение YAML и дерева должно
остановить бота при запуске, а сломанная правка YAML на ходу — не ронять ответы.
"""

import os

import pytest

from src.bot.dialogs import DialogFileError, Line, load_texts
from src.bot.dialogs.generate import TREE_PATH, render_tree
from src.bot.dialogs.texts import signatures
from src.bot.services.dialog import DialogService

EXPECTED = {"coffee.cooldown": frozenset({"minutes"}), "bot": frozenset()}


def write(folder, text: str, mtime: int) -> None:
    path = folder / "texts.yaml"
    path.write_text(text, "utf-8")
    os.utime(path, (mtime, mtime))


def test_tree_matches_yaml():
    assert render_tree(signatures(load_texts())) == TREE_PATH.read_text("utf-8"), (
        "tree.py отстал от YAML: python -m src.bot.dialogs.generate"
    )


@pytest.mark.parametrize(
    ("yaml_text", "problem"),
    [
        ("coffee:\n  cooldown: Жди {seconds}\nbot: Чо\n", "coffee.cooldown: подстановки"),
        ("bot: Чо\n", "coffee.cooldown: нет текста"),
        ("coffee:\n  cooldown: '{minutes}'\nbot: Чо\nstart: Привет\n", "start: нет в коде"),
        ("coffee:\n  cooldown: Жди {minutes\nbot: Чо\n", "фигурные скобки"),
        ("coffee: [1, 2]\nbot: Чо\n", "нужен текст"),
    ],
)
def test_startup_rejects_texts_that_do_not_match_code(tmp_path, yaml_text, problem):
    write(tmp_path, yaml_text, mtime=1)

    with pytest.raises(DialogFileError, match=problem):
        DialogService(tmp_path, EXPECTED)


def test_broken_edit_keeps_previous_texts_until_fixed(tmp_path):
    write(tmp_path, "coffee:\n  cooldown: Жди {minutes} мин\nbot: Чо\n", mtime=1)
    dialogs = DialogService(tmp_path, EXPECTED)
    cooldown = Line("coffee.cooldown", {"minutes": 5})

    write(tmp_path, "coffee:\n  cooldown: Жди {seconds} сек\nbot: Чо\n", mtime=2)
    assert dialogs.text(cooldown) == "Жди 5 мин"

    # вариант может взять не все подстановки фразы
    write(tmp_path, "coffee:\n  cooldown:\n  - Жди {minutes}\n  - Жди\nbot: Чо\n", mtime=3)
    assert {dialogs.text(cooldown) for _ in range(50)} == {"Жди 5", "Жди"}
