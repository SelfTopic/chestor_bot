from selfrot import BaseRouter

from ....context import AppContext
from .consent import (
    FamilyConsentLinkHandler,
    MalformedMarriageButtonHandler,
    NotYourMarriageButtonHandler,
    ProposalAnswerHandler,
)
from .family import DivorceHandler, DivorcePressHandler, FamilyHandler
from .propose import ProposalHandler, ProposalPaymentHandler, ProposalRepliedHandler
from .ticker import MarriageTicker


class MarriageLinkRouter(BaseRouter[AppContext]):
    handlers = (FamilyConsentLinkHandler,)


class MarriageRouter(BaseRouter[AppContext]):
    handlers = (
        ProposalRepliedHandler,
        ProposalHandler,
        ProposalPaymentHandler,
        ProposalAnswerHandler,
        FamilyHandler,
        DivorceHandler,
        DivorcePressHandler,
        NotYourMarriageButtonHandler,
        MalformedMarriageButtonHandler,
    )


__all__ = ["MarriageLinkRouter", "MarriageRouter", "MarriageTicker"]
