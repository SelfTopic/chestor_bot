"""
Раскладка порта по правилу из CLAUDE.md («Где что лежит»), проверяемая по графу
импортов src/bot. Тесты пользователями не считаются.

- Слои по ролям — корень (context.py, bot.py, …), services/, repositories/,
  middlewares/ — не импортируют routers/; собирает всё только __main__.
- Модуль в корне нужен не только роутерам: иначе его место в routers/.
- Модуль в routers/ лежит ровно в самой глубокой общей папке тех, кто его
  импортирует: не выше (тогда он уезжает к единственному пакету-пользователю) и
  не вбок (соседний пакет импортирует его — значит, поднять до общей папки).
"""

import ast
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PORT = REPO / "src" / "bot"
ROUTERS = PORT / "routers"
LAYERS = ("services", "repositories", "middlewares")


def _module_name(path: Path) -> str:
    parts = path.relative_to(REPO).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _port_modules() -> dict[str, Path]:
    return {
        _module_name(path): path
        for path in PORT.rglob("*.py")
        if "__pycache__" not in path.parts
    }


def _imports(path: Path, modules: dict[str, Path]) -> set[str]:
    """Модули порта, которые импортирует файл (с учётом относительных импортов)."""
    name = _module_name(path)
    package = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            base = package.split(".")[: len(package.split(".")) - (node.level - 1)]
            target = ".".join(base + ([node.module] if node.module else []))
        else:
            target = node.module or ""
        for alias in node.names:
            submodule = f"{target}.{alias.name}"
            found.add(submodule if submodule in modules else target)
    return {m for m in found if m in modules and m != name}


def _importers() -> tuple[dict[str, Path], dict[str, set[str]]]:
    modules = _port_modules()
    importers: dict[str, set[str]] = defaultdict(set)
    for name, path in modules.items():
        for target in _imports(path, modules):
            importers[target].add(name)
    return modules, importers


def _lowest_common_dir(paths: list[Path]) -> Path:
    common = paths[0].parent
    for path in paths[1:]:
        while not path.is_relative_to(common):
            common = common.parent
    return common


def _rel(path: Path) -> str:
    return str(path.relative_to(PORT))


def test_lower_layers_do_not_import_routers():
    modules = _port_modules()
    problems = []
    for name, path in modules.items():
        if path.is_relative_to(ROUTERS) or path.name == "__main__.py":
            continue
        routers = sorted(
            _rel(modules[m]) for m in _imports(path, modules) if modules[m].is_relative_to(ROUTERS)
        )
        if routers:
            problems.append(f"{_rel(path)} импортирует {routers}")

    assert not problems, "Нижний слой импортирует роутеры:\n" + "\n".join(problems)


def test_root_modules_are_not_router_only():
    modules, importers = _importers()
    problems = []
    for name, path in modules.items():
        if path.parent != PORT or path.name in ("__init__.py", "__main__.py"):
            continue
        users = importers[name]
        if users and all(modules[u].is_relative_to(ROUTERS) for u in users):
            where = _lowest_common_dir([modules[u] for u in users])
            problems.append(f"{_rel(path)}: нужен только роутерам — место в {_rel(where)}/")

    assert not problems, "Модуль корня нужен только роутерам:\n" + "\n".join(problems)


def test_router_modules_live_where_their_users_meet():
    modules, importers = _importers()
    problems = []
    for name, path in modules.items():
        if not path.is_relative_to(ROUTERS) or path.name == "__init__.py":
            continue
        users = importers[name]
        if not users:
            problems.append(f"{_rel(path)}: никто не импортирует")
            continue
        where = _lowest_common_dir([modules[u] for u in users])
        if where != path.parent:
            names = sorted(_rel(modules[u]) for u in users)
            problems.append(f"{_rel(path)}: место в {_rel(where)}/ (импортируют {names})")

    assert not problems, "Модуль routers/ лежит не там, где его пользователи:\n" + "\n".join(
        problems
    )


def test_the_checks_see_the_graph():
    """Страховка от молча пустого графа: известные связи находятся."""
    modules, importers = _importers()
    assert "src.bot.routers.rich" in importers
    assert "src.bot.routers.ghoul_routers.battle_text" in importers[
        "src.bot.routers.rich"
    ]
    assert len(modules) > 100
