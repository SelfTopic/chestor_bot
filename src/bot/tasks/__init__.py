from pathlib import Path
from typing import Any

from selfrot import BaseTask, Every

from src.config import settings

from ..context import AppContext
from ..routers import (
    expire_overdue_duels,
    expire_overdue_streaks,
    expire_overdue_votes,
    reward_cult_hashtags,
)
from ..services.analytics import FLUSH_INTERVAL
from ..services.media_tools import TOOLS_UPDATE_INTERVAL, MediaToolsUpdater
from ..services.moderation import ModerationTicker
from ..services.notification_ticker import NotificationTicker


class DuelExpiry(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        await expire_overdue_duels(self.ctx, self.ctx.bot)


class FamilyVoteExpiry(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        await expire_overdue_votes(self.ctx, self.ctx.bot)


class QuizStreakExpiry(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        await expire_overdue_streaks(self.ctx, self.ctx.bot)


class CultReward(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        await reward_cult_hashtags(self.ctx, self.ctx.bot)


class Notifications(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        ctx = self.ctx
        await NotificationTicker(ctx.session_factory, ctx.notifier, ctx.dialog_service).tick()


class ModerationExpiry(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        ctx = self.ctx
        await ModerationTicker(ctx.session_factory, ctx.notifier, ctx.dialog_service).tick()


class AnalyticsFlush(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        await self.ctx.analytics.flush()


class MediaToolsUpdate(BaseTask[AppContext[Any]]):
    async def run(self) -> None:
        if self.ctx.link_media_service.enabled:
            await MediaToolsUpdater(Path(settings.MEDIA_TOOLS_DIR)).tick()


TASKS = (
    Every(1, DuelExpiry),
    Every(30, FamilyVoteExpiry),
    Every(10, QuizStreakExpiry),
    Every(30, Notifications),
    # Сам час отсчитывает отметка выплаты в БД: перезапуск бота его не сбивает.
    Every(300, CultReward),
    Every(10, ModerationExpiry),
    Every(FLUSH_INTERVAL, AnalyticsFlush),
    Every(TOOLS_UPDATE_INTERVAL, MediaToolsUpdate),
)

__all__ = [
    "TASKS",
    "AnalyticsFlush",
    "CultReward",
    "QuizStreakExpiry",
    "DuelExpiry",
    "FamilyVoteExpiry",
    "MediaToolsUpdate",
    "ModerationExpiry",
    "Notifications",
]
