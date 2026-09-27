from typing import Literal

ChatTextKind = Literal["rules", "welcome", "goodbye"]


class ChatError(Exception): ...


class ChatTextLengthError(ChatError):
    def __init__(self, kind: ChatTextKind) -> None:
        super().__init__(kind)
        self.kind: ChatTextKind = kind
