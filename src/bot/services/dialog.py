import json
import os
import time
import logging
import random
from typing import Dict, List, Any, Union

logger = logging.getLogger(__name__)

class DialogService:
    
    filename: str = "dialogs.json"
    cache: Dict[str, Union[str, List[str]]]
    last_mtime: float
    
    def __init__(self, filename: str = "dialogs.json") -> None:
        logger.debug(f"Called DialogService constructor. Params: filename={filename}")
        
        self.filename = filename
        self.cache: Dict[str, Union[str, List[str]]] = {}
        self.last_mtime: float = 0
        self._load_data()
        
        logger.debug("DialogService initialized successfully")

    def _load_data(self) -> None:
        logger.debug(f"Called _load_data. File: {self.filename}")
        
        try:
            current_mtime = os.path.getmtime(self.filename)
            if current_mtime > self.last_mtime:
                logger.debug("File modified, loading new data")
                
                with open(self.filename, "r", encoding="utf-8") as json_data:
                    self.cache = json.load(json_data)

                self.last_mtime = current_mtime
                logger.info(f"Dialog data reloaded from {self.filename}. Keys loaded: {len(self.cache)}")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading dialog data: {str(e)}")
            
            if not self.cache:
                logger.critical("Initial data load failed and no cache available")
                raise RuntimeError(f"Initial data load failed: {str(e)}")

    def _reload_if_needed(self) -> None:
        logger.debug("Called _reload_if_needed")
        
        try:
            current_mtime = os.path.getmtime(self.filename)
            if current_mtime > self.last_mtime:
                logger.debug("File changed detected, reloading data")
                self._load_data()
            else:
                logger.debug("No file changes detected")

        except FileNotFoundError:
            logger.error(f"Dialog file not found: {self.filename}")

    def text(self, key: str, **kwargs: Any) -> str:
        logger.debug(f"Called text method. Params: key={key}, kwargs={kwargs}")
        
        self._reload_if_needed()
        
        if key not in self.cache:
            logger.error(f"Key '{key}' not found in dialog data")
            raise KeyError(f"Key '{key}' not found in dialog data")
        
        value = self.cache[key]
        
        if not isinstance(value, str):
            logger.error(f"Value for key '{key}' is not a string")
            raise TypeError(f"Value for key '{key}' is not a string")
        
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + str(key) + "}"
        
        result = value.format_map(SafeDict(kwargs))
        logger.debug(f"Text formatted successfully. Result length: {len(result)}")
        
        return result

    def random(self, key: str, **kwargs: str) -> str:
        logger.debug(f"Called random method. Params: key={key}, kwargs={kwargs}")
        
        self._reload_if_needed()
        
        if key not in self.cache:
            logger.error(f"Key '{key}' not found in dialog data")
            raise KeyError(f"Key '{key}' not found in dialog data")
        
        value = self.cache[key]
        
        if not isinstance(value, list):
            logger.error(f"Value for key '{key}' is not a list")
            raise TypeError(f"Value for key '{key}' is not a list")
        
        if not value:
            logger.error(f"List for key '{key}' is empty")
            raise ValueError(f"List for key '{key}' is empty")
        
        if not all(isinstance(item, str) for item in value):
            logger.error(f"List for key '{key}' contains non-string items")
            raise TypeError(f"List for key '{key}' contains non-string items")
        
        selected = random.choice(value)
        logger.debug(f"Random item selected from list of {len(value)} items")
        
        class SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"
        
        result = selected.format_map(SafeDict(kwargs))
        logger.debug(f"Random text formatted successfully. Result length: {len(result)}")
        
        return result

__all__ = ["DialogService"]