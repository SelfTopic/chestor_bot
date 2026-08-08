import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
print(f"Loading environment variables from: {env_path}")
load_dotenv(env_path)


class Config:
    API_ID: int = int(os.getenv("API_ID", 0))
    API_HASH: str = os.getenv("API_HASH", "")
    PHONE_NUMBER: str = os.getenv("PHONE_NUMBER", "")
    PASSWORD: str = os.getenv("PASSWORD", "")
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
    DOWNLOAD_PATH: str | Path = os.getenv("DOWNLOAD_PATH", "")

    SEASONS_COUNT = 4
    SERIES_COUNT = 12

    def __init__(self):
        if (
            self.API_ID == 0
            or not self.API_HASH
            or not self.PHONE_NUMBER
            or self.CHANNEL_ID == 0
            or not self.DOWNLOAD_PATH
        ):
            raise ValueError(
                "API_ID, API_HASH, PHONE_NUMBER, CHANNEL_ID, and DOWNLOAD_PATH must be set in environment variables."
            )
        self.DOWNLOAD_PATH = Path(self.DOWNLOAD_PATH).resolve()


config = Config()
