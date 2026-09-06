from os import environ

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()


url = URL.create(
    "postgresql+psycopg",
    username=environ.get("POSTGRES_USERNAME", default="postgres"),
    password=environ.get("POSTGRES_PASSWORD", default="changeme"),
    host=environ.get("POSTGRES_HOSTNAME", default="localhost"),
    database=environ.get("POSTGRES_DATABASE", default="postgres"),
    port=5432,
)

engine = create_async_engine(url=url, echo=False, pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
