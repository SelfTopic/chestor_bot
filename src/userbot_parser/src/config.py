import os


class Config:
    API_ID: int = int(os.getenv("API_ID", 0))
    API_HASH: str = os.getenv("API_HASH", "")
    PHONE_NUMBER: str = os.getenv("PHONE_NUMBER", "")
    PASSWORD: str = os.getenv("PASSWORD", "")
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", 0))
    DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "")

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


config = Config()
