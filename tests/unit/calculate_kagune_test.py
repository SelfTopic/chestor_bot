import pytest

from src.bot.utils import calculate_kagune

def test_kagune_calculation():

    assert len(calculate_kagune(3)) == 2
    
    with pytest.raises(ValueError):
        calculate_kagune(16)
    
    with pytest.raises(ValueError):
        calculate_kagune(-1)
    
    assert len(calculate_kagune(15)) == 4