from src.bot.types import KaguneType

TYPE_BY_NAME = {kt.value["name_english"]: kt for kt in KaguneType}
TYPE_NAMES = ", ".join(sorted(TYPE_BY_NAME))
