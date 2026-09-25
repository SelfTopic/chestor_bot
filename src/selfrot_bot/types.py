from selfrot.types import (
    CaptionMessage,
    DataCallbackQuery,
    MessageCallbackQuery,
    ReplyToMessageMessage,
    ReplyUserMessage,
    TextMessage,
    UserMessage,
)

# Библиотека даёт по одному суженному типу на поле; нужные сочетания собираются
# наследованием (все поля, обещанные обоими, гарантируют фильтры через `&`).


class TextUserMessage(TextMessage, UserMessage, frozen=True):
    """Сообщение с текстом и отправителем."""


class TextUserReplyMessage(TextUserMessage, ReplyUserMessage, frozen=True):
    """Сообщение с текстом и отправителем, написанное в ответ на сообщение с отправителем."""


class TextUserReplyToMessage(TextUserMessage, ReplyToMessageMessage, frozen=True):
    """Сообщение с текстом и отправителем, написанное в ответ на любое сообщение (без
    требований к самому ответу — какое медиа там лежит, хендлер смотрит сам)."""


class DataMessageCallbackQuery(DataCallbackQuery, MessageCallbackQuery, frozen=True):
    """Нажатие кнопки с данными и с сообщением под кнопкой."""


__all__ = [
    "CaptionMessage",
    "DataMessageCallbackQuery",
    "ReplyUserMessage",
    "TextMessage",
    "TextUserMessage",
    "TextUserReplyMessage",
    "TextUserReplyToMessage",
    "UserMessage",
]
