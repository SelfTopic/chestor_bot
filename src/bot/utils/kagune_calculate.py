import logging

from ..types import KaguneType

logger = logging.getLogger(__name__)

def calculate_kagune(bit: int) -> list[KaguneType]:
    logger.debug("Util calculate kagune called")

    if bit < 0:
        logger.error(f"Invalid bit mask: {bit}. Value cannot be negative")
        raise ValueError(f"Invalid bit mask: {bit}. Value cannot be negative")


    valid_bits = [k.value["bit"] for k in KaguneType]
    max_valid_bit = sum(valid_bits) 
    

    if bit > max_valid_bit:
        logger.error(
            f"Invalid bit mask: {bit}. "
            f"Maximum allowed value: {max_valid_bit} "
            f"(bits: {', '.join(str(b) for b in valid_bits)})"    
        )

        raise ValueError(
            f"Invalid bit mask: {bit}. "
            f"Maximum allowed value: {max_valid_bit} "
            f"(bits: {', '.join(str(b) for b in valid_bits)})"
        )
    

    invalid_bits = []
    for i in range(0, bit.bit_length()):
        current_bit = 1 << i  
        if bit & current_bit:  
            if current_bit not in valid_bits:
                invalid_bits.append(current_bit)
    
    if invalid_bits:
        logger.error(f"invalid bits: {', '.join(str(b) for b in invalid_bits)}. ")
        raise ValueError(
            f"invalid bits: {', '.join(str(b) for b in invalid_bits)}. "
            f"valid bits: {', '.join(str(b) for b in valid_bits)}"
        )
    

    result = []

    for kagune in KaguneType:
        if bit & kagune.value["bit"]:
            result.append(kagune)
    
    logger.debug(f"Util calculate kagune is sucsessfull finished. Return result: {result}")
    return result