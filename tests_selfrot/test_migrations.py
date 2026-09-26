"""
Миграции с нуля до головы — так, как их запускает свежий клон: alembic.ini нет,
настройки из [tool.alembic] pyproject.toml, адрес БД из POSTGRES_* (src.database),
драйвер psycopg 3. Отдельная пустая база в том же тестовом Postgres.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

REPO = Path(__file__).resolve().parent.parent
DATABASE = "migrations_check"


def _alembic(args: list[str], env: dict[str, str], ini: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ini), *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_migrations_upgrade_empty_database_to_head(postgres_url, tmp_path):
    server = urlsplit(postgres_url)
    assert server.hostname and server.port and server.username and server.password
    admin = (
        f"postgresql://{server.username}:{server.password}"
        f"@{server.hostname}:{server.port}{server.path}"
    )
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {DATABASE}")
        conn.execute(f"CREATE DATABASE {DATABASE}")

    env = {
        **os.environ,
        "POSTGRES_HOSTNAME": server.hostname,
        "POSTGRES_PORT": str(server.port),
        "POSTGRES_USERNAME": server.username,
        "POSTGRES_PASSWORD": server.password,
        "POSTGRES_DATABASE": DATABASE,
    }
    no_ini = tmp_path / "alembic.ini"  # такого файла нет: только pyproject.toml

    upgraded = _alembic(["upgrade", "head"], env, no_ini)
    assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr

    heads = _alembic(["heads"], env, no_ini)
    assert heads.returncode == 0, heads.stdout + heads.stderr
    (head,) = [line.split()[0] for line in heads.stdout.splitlines() if "(head)" in line]

    with psycopg.connect(admin.rsplit("/", 1)[0] + f"/{DATABASE}") as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    assert row == (head,)
