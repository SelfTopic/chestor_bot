from selfrot import BaseRouter

from ...context import AppContext
from .marriage import MarriageLinkRouter, MarriageRouter, expire_overdue_votes
from .nickname import NicknameRouter


class CommunityRouter(BaseRouter[AppContext]):
    routers = (MarriageLinkRouter, MarriageRouter, NicknameRouter)


__all__ = ["CommunityRouter", "expire_overdue_votes"]
