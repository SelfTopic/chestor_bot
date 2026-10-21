from selfrot import BaseRouter

from ...context import AppContext
from .marriage import MarriageLinkRouter, MarriageRouter, expire_overdue_votes


class CommunityRouter(BaseRouter[AppContext]):
    routers = (MarriageLinkRouter, MarriageRouter)


__all__ = ["CommunityRouter", "expire_overdue_votes"]
