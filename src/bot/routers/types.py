from selfrot.types import (
    CaptionMessage,
    DataCallbackQuery,
    MessageCallbackQuery,
    ReplyToMessageMessage,
    ReplyUserMessage,
    TextMessage,
    UserMessage,
)


class TextUserMessage(TextMessage, UserMessage, frozen=True):
    pass
class TextUserReplyMessage(TextUserMessage, ReplyUserMessage, frozen=True):
    pass
class TextUserReplyToMessage(TextUserMessage, ReplyToMessageMessage, frozen=True):
    pass
class DataMessageCallbackQuery(DataCallbackQuery, MessageCallbackQuery, frozen=True):
    pass
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
