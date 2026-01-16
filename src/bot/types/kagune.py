from enum import Enum


class KaguneType(Enum):
    
    UKAKU = {
        "k": 1,
        "name": "Укаку",
        "bit": 1    
    }

    KOUKAKU = {
        "k": 1.2,
        "name": "Коукаку",
        "bit": 2    
    }

    RINKAKU = {
        "k": 1.4,
        "name": "Ринкаку",
        "bit": 4    
    }

    BIKAKU = {
        "k": 1.6,
        "name": "Бикаку",
        "bit": 8    
    }

