from selfrot.types import User


def full_name(user: User) -> str:
    """Как aiogram User.full_name: имя и фамилия через пробел."""
    return f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
