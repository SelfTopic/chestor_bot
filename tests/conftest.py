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
        environment={"POSTGRES_USER": "test", "POSTGRES_PASSWORD": "test", "POSTGRES_DB": "test_db"},
        detach=True,
        remove=True
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
