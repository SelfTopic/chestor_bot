from .admin import UnknownStatField
from .battle import (
    BattleError,
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from .chat import ChatError, ChatTextLengthError
from .chat_not_found import ChatNotFound, ChatNotFoundInDatabase
from .media_download import (
    CollectionNotFoundError,
    InvalidMediaRequestError,
    MediaError,
    MediaNotFoundError,
    ValidationMediaError,
)
from .ghoul import GhoulNotFound, KaguneAlreadyOwned, KaguneNotOwned, LastKaguneType
from .lottery import (
    BetOutOfRange,
    LotteryError,
    LotteryPlayerMissing,
    NotEnoughMoneyForBet,
    UnknownLotteryColor,
)
from .media_not_found import MediaNotFound, MediaNotFoundInDatabase
from .rp_commands import RpCommandError, RpCommandLimitReached, RpCommandNotFound
from .time import DurationParseError
from .transfer import (
    InsufficientBalanceError,
    InvalidTransferAmountError,
    ReceiverLimitExceededError,
    ReceiverMissingError,
    ReceiverVanishedError,
    SelfTransferError,
    SenderMissingError,
    SenderTooNewError,
    TransferError,
)
from .user_not_found import UserNotFound
from .wordle import WordleGuessError, WordleNotRussian, WordleWrongLength

__all__ = [
    "BattleError",
    "FighterHasPendingBattleError",
    "FighterIsDeadError",
    "FighterNotCombatReadyError",
    "ChatError",
    "ChatTextLengthError",
    "ChatNotFound",
    "ChatNotFoundInDatabase",
    "MediaError",
    "MediaNotFoundError",
    "InvalidMediaRequestError",
    "UserNotFound",
    "UnknownStatField",
    "WordleGuessError",
    "WordleNotRussian",
    "WordleWrongLength",
    "CollectionNotFoundError",
    "ValidationMediaError",
    "MediaNotFoundInDatabase",
    "MediaNotFound",
    "RpCommandLimitReached",
    "RpCommandNotFound",
    "RpCommandError",
    "DurationParseError",
    "GhoulNotFound",
    "KaguneAlreadyOwned",
    "KaguneNotOwned",
    "LastKaguneType",
    "LotteryError",
    "BetOutOfRange",
    "NotEnoughMoneyForBet",
    "LotteryPlayerMissing",
    "UnknownLotteryColor",
    "TransferError",
    "InvalidTransferAmountError",
    "SelfTransferError",
    "InsufficientBalanceError",
    "SenderTooNewError",
    "ReceiverLimitExceededError",
    "ReceiverMissingError",
    "ReceiverVanishedError",
    "SenderMissingError",
]
