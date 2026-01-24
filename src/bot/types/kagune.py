from enum import Enum


class KaguneType(Enum):
    UKAKU = {"k": 1, "name": "Укаку", "name_english": "ukaku", "bit": 1}

    KOUKAKU = {"k": 1.2, "name": "Коукаку", "name_english": "koukaku", "bit": 2}

    RINKAKU = {"k": 1.4, "name": "Ринкаку", "name_english": "rinkaku", "bit": 4}

    BIKAKU = {"k": 1.6, "name": "Бикаку", "name_english": "bikaku", "bit": 8}
