from selfrot import BaseRouter

from ....context import AppContext
from .consent import (
    FamilyConsentLinkHandler,
    MalformedMarriageButtonHandler,
    NotYourMarriageButtonHandler,
    ProposalAnswerHandler,
)
from .family import DivorceHandler, DivorcePressHandler, FamiliesHandler, FamilyHandler
from .propose import ProposalHandler, ProposalPaymentHandler, ProposalRepliedHandler
from .rename import RenameAnswerHandler, RenameHandler, RenameLinkHandler
from .ticker import MarriageTicker


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
        MalformedMarriageButtonHandler,
    )


__all__ = ["MarriageLinkRouter", "MarriageRouter", "MarriageTicker"]
