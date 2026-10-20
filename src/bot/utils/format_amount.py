def format_amount(value: int) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value):,}".replace(",", ".")
