import time

import docker
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from src.database.models import Base

TEST_DB_URL = "postgresql+psycopg://test:test@localhost:5433/test_db"


@pytest.fixture(scope="session", autouse=True)
def pg_container():
    client = docker.from_env()
    container = client.containers.run(
        "postgres:16-alpine",
        ports={"5432/tcp": 5433},
        environment={
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB": "test_db",
        },
        detach=True,
        remove=True,
    )
    for line in container.logs(stream=True):
        if "database system is ready to accept connections" in line.decode():
            break
    time.sleep(0.4)
    yield
    container.stop()


@pytest.fixture
async def engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def user_repo(session):
    from src.bot.repositories.user import UserRepository

    return UserRepository(session)


@pytest.fixture
def ghoul_repo(session):
    from src.bot.repositories.ghoul import GhoulRepository

    return GhoulRepository(session)


@pytest.fixture
def make_user(user_repo):
    async def _make(
        telegram_id: int = 100_000_001,
        first_name: str = "Test",
        last_name: str | None = None,
        username: str | None = "testuser",
    ):
        return await user_repo.upsert(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )

    return _make


@pytest.fixture
def make_ghoul(ghoul_repo):
    async def _make(telegram_id: int = 100_000_001, **kwargs):
        return await ghoul_repo.upsert(telegram_id=telegram_id, **kwargs)

    return _make
