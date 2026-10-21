from selfrot import BaseRouter

from ....context import AppContext
from .consent import (
    FamilyConsentLinkHandler,
    NotYourMarriageButtonHandler,
    ProposalAnswerHandler,
)
from .family import DivorceHandler, DivorcePressHandler, FamiliesHandler, FamilyHandler
from .propose import ProposalHandler, ProposalPaymentHandler, ProposalRepliedHandler
from .rename import RenameAnswerHandler, RenameHandler, RenameLinkHandler
from .expiry import expire_overdue_votes


class MarriageLinkRouter(BaseRouter[AppContext]):
    handlers = (FamilyConsentLinkHandler, RenameLinkHandler)


class MarriageRouter(BaseRouter[AppContext]):
    handlers = (
        ProposalRepliedHandler,
        ProposalHandler,
        ProposalPaymentHandler,
        ProposalAnswerHandler,
        FamilyHandler,
        FamiliesHandler,
        RenameHandler,
        RenameAnswerHandler,
        DivorceHandler,
        DivorcePressHandler,
        NotYourMarriageButtonHandler,
    )


__all__ = ["MarriageLinkRouter", "MarriageRouter", "expire_overdue_votes"]
