from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr = Field(default=...)
    ADMIN_IDS: List[int] = Field(default_factory=list)
    ENV: str = Field(default="DEV")

    POSTGRES_DATABASE: str = Field(default=...)
    POSTGRES_USERNAME: str = Field(default=...)
    POSTGRES_PASSWORD: str = Field(default=...)
    POSTGRES_HOSTNAME: str = Field(default=...)
    PGADMIN_DEFAULT_EMAIL: str = Field(default=...)
    PGADMIN_DEFAULT_PASSWORD: str = Field(default=...)

    GHOUL_QUIZ_API_KEY: SecretStr = Field(default=...)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf8")


settings = Settings()

__all__ = ["settings"]
