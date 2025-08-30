import json
import os
import time
import logging
import random
from typing import Self, Dict, List, Any, Union

logger = logging.getLogger(__name__)

class DialogService:
    """
    Service for managing dialog content with automatic file reloading.
    
    Args:
        filename: Path to JSON file containing dialog content
        
    Attributes:
        filename: Path to dialog JSON file
        cache: Cached dialog content
        last_mtime: Last modification time of file
    """
    
    filename: str = "dialogs,json"
    cache: Dict[str, Union[str, List[str]]]
    last_mtime: float
    
    def __init__(self, filename: str = "dialogs.json") -> None:
        self.filename = filename
        self.cache: Dict[str, Union[str, List[str]]] = {}
        self.last_mtime: float = 0
        self._load_data()

    def _load_data(self) -> None:
        """Loads or reloads dialog data when file changes"""
        try:

            current_mtime = os.path.getmtime(self.filename)
            if current_mtime > self.last_mtime:

                with open(self.filename, "r", encoding="utf-8") as json_data:
                    self.cache = json.load(json_data)

                self.last_mtime = current_mtime

                logger.info(f"Dialog data reloaded from {self.filename}")

        except (FileNotFoundError, json.JSONDecodeError) as e:

            logger.error(f"Error loading dialog data: {str(e)}")

            if not self.cache:
                raise RuntimeError(f"Initial data load failed: {str(e)}")

    def _reload_if_needed(self) -> None:
        """Checks if file has changed and reloads if necessary"""

        try:

            current_mtime = os.path.getmtime(self.filename)
            if current_mtime > self.last_mtime:
                self._load_data()

        except FileNotFoundError:
            logger.error(f"Dialog file not found: {self.filename}")

    def text(
        self, 
        key: str,
        **kwargs: str
    ) -> str:
        """
        Retrieves a text string by key and formats it
        
        Args:
            key: Dialog key to retrieve
            kwargs: Formatting parameters
            
        Returns:
            Formatted text string
            
        Raises:
            KeyError: If key is not found
            TypeError: If value is not a string
        """
        self._reload_if_needed()
        
        if key not in self.cache:
            raise KeyError(f"Key '{key}' not found in dialog data")
        
        value = self.cache[key]
        
        if not isinstance(value, str):
            raise TypeError(f"Value for key '{key}' is not a string")
        
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        
        return value.format_map(SafeDict(kwargs))

    def random(
        self,
        key: str,
        **kwargs: str
    ) -> str:
        """
        Retrieves a random text from a list by key and formats it
        
        Args:
            key: Dialog key to retrieve
            kwargs: Formatting parameters
            
        Returns:
            Formatted random text string
            
        Raises:
            KeyError: If key is not found
            TypeError: If value is not a list of strings
        """
        self._reload_if_needed()
        
        if key not in self.cache:
            raise KeyError(f"Key '{key}' not found in dialog data")
        
        value = self.cache[key]
        
        if not isinstance(value, list):
            raise TypeError(f"Value for key '{key}' is not a list")
        
        if not value:
            raise ValueError(f"List for key '{key}' is empty")
        
        if not all(isinstance(item, str) for item in value):
            raise TypeError(f"List for key '{key}' contains non-string items")
        
        selected = random.choice(value)
        
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        
        return selected.format_map(SafeDict(kwargs))

__all__ = ["DialogService"]