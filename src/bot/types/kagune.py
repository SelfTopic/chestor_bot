from enum import Enum


class KaguneType(Enum):
    UKAKU = {
        "k": 1,
        "name": "Укаку",
        "name_english": "ukaku",
        "bit": 1,
        "strength_column": "kagune_strength_ukaku",
    }

    KOUKAKU = {
        "k": 1.2,
        "name": "Коукаку",
        "name_english": "koukaku",
        "bit": 2,
        "strength_column": "kagune_strength_koukaku",
    }

    RINKAKU = {
        "k": 1.4,
        "name": "Ринкаку",
        "name_english": "rinkaku",
        "bit": 4,
        "strength_column": "kagune_strength_rinkaku",
    }

    BIKAKU = {
        "k": 1.6,
        "name": "Бикаку",
        "name_english": "bikaku",
        "bit": 8,
        "strength_column": "kagune_strength_bikaku",
    }
