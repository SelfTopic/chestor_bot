import logging
from collections.abc import Iterator
from contextlib import contextmanager

from selfrot.exceptions import MessageNotModified, MessageToEditNotFound, TelegramAPIError
from selfrot.types import User

logger = logging.getLogger(__name__)


def full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}" if user.last_name else user.first_name


# Правка уже отправленного сообщения не шаг сценария: её сбой не должен прерывать дуэль или
# брак. «Нечего менять» и «сообщения уже нет» — норма, остальное — в лог.
@contextmanager
def quiet_edit(what: str) -> Iterator[None]:
    try:
        yield
    except (MessageNotModified, MessageToEditNotFound):
        pass
    except TelegramAPIError:
        logger.warning("%s: не удалось править сообщение", what, exc_info=True)
