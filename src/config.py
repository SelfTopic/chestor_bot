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
    LLM_API_KEY: SecretStr = Field(default=SecretStr(""))
    LLM_BASE_URL: str = Field(default="https://foundation-models.api.cloud.ru/v1")
    ROAST_ENABLED: bool = Field(default=False)
    ROAST_MODEL: str = Field(default="deepseek-ai/DeepSeek-V4-Pro")
    ROAST_CLASSIFIER_MODEL: str = Field(default="Qwen/Qwen3.6-35B-A3B")
    ROAST_DAILY_LIMIT: int = Field(default=500)
    ROAST_TIMEOUT: float = Field(default=25.0)

    HTTP_PROXY: str = Field(default="")
    HTTPS_PROXY: str = Field(default="")
    ALL_PROXY: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf8", extra="ignore"
    )


settings = Settings()

__all__ = ["settings"]
