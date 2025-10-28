from dataclasses import dataclass 


@dataclass 
class KaguneConfig:
    base_price: int = 100
    exponent: float = 1.7 
    linear_multiplier: int = 50

KAGUNE_CONFIG = KaguneConfig()