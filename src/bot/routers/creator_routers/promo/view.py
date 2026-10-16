from typing import Any

from src.bot.dialogs import Dialogs, Line
from src.bot.services.promo import Granted, PromoStatus, promo_status
from src.bot.utils import format_duration, utcnow_naive
from src.database.models import PromoCode

from ....context import AppContext
from ...promo_rewards import reward_lines
from .dates import moscow_time

PHRASES = Dialogs.admin.promo

STATUS_LINES = {
    PromoStatus.ACTIVE: PHRASES.status.active,
    PromoStatus.EXPIRED: PHRASES.status.expired,
    PromoStatus.EXHAUSTED: PHRASES.status.exhausted,
    PromoStatus.DELETED: PHRASES.status.deleted,
}


def app_context(ctx: Any) -> AppContext[Any]:
    assert isinstance(ctx, AppContext)
    return ctx


def status_text(ctx: AppContext[Any], promo: PromoCode) -> str:
    return ctx.text(STATUS_LINES[promo_status(promo, utcnow_naive())]())


def rewards_text(ctx: AppContext[Any], promo: PromoCode) -> str:
    granted = [Granted(reward) for reward in ctx.promo_service.rewards(promo)]
    return reward_lines(ctx, granted)


def activations_text(ctx: AppContext[Any], promo: PromoCode) -> str:
    used, limit = promo.activations_used, promo.activations_limit
    return ctx.text(PHRASES.card.activations_value(used=used, limit=limit))


def term_line(promo: PromoCode) -> Line:
    if promo.expires_at is None:
        return PHRASES.forever()
    left = int((promo.expires_at - utcnow_naive()).total_seconds())
    date = moscow_time(promo.expires_at)
    if left <= 0:
        return PHRASES.card.expired_at(date=date)
    return PHRASES.card.until(date=date, left=format_duration(left))
