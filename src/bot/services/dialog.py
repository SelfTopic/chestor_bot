import json

from typing import Self
import logging 

logger = logging.getLogger(__name__)

class DialogService:

    filename: str = "dialogs.json"

    def __init__(self, filename: str = "dialogs.json") -> None:

        self.filename = filename
        
        with open(filename, "r") as json_data:
            self.cache: dict[str, str] = json.loads(json_data.read())

    def text(
        self: Self, 
        key: str,
        **kwargs: str    
    ) -> str:
        
        value = self.cache.get(key)

        if not value:
            raise ValueError("Key not found")
        
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        
        logger.debug(f"string for formating: {value}")
        value = value.format_map(SafeDict(kwargs))

        return value

__all__ = ["DialogService"]
