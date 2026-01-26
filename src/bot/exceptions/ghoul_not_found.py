class GhoulNotFound(Exception):
    """Common base class for not found ghouls"""


class GhoulNotFoundInDatabase(GhoulNotFound): ...
