from enum import Enum 


class Race(Enum):

    HUMAN = {
        "bit": 0,
        "name": "Человек"    
    }
    GHOUL = {
        "bit": 1,
        "name": "Гуль"    
    }
    CCG = {
        "bit": 2,
        "name": "Человек. Агент ССG"    
    }