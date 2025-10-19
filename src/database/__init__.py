from os import environ

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    async_sessionmaker, 
    create_async_engine, 
    AsyncEngine
)

from .models import Base

load_dotenv()


url = URL.create(
    'postgresql+psycopg',
    username=environ.get('POSTGRES_USERNAME', default='postgres'),
    password=environ.get('POSTGRES_PASSWORD', default='changeme'),
    host=environ.get('POSTGRES_HOSTNAME', default='localhost'),
    database=environ.get('POSTGRES_DATABASE', default='postgres'),
    port=5432
)

engine = create_async_engine(url=url, echo=False)
session_factory = async_sessionmaker(engine)


async def flush_database(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def create_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)