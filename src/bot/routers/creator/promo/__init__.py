from selfrot import BaseRouter

from ....context import AppContext
from .card import PromoCardHandler, PromoCardPressHandler
from .catalog import PromoCatalogHandler, PromoCatalogPressHandler
from .create import CreatePromoHandler


class PromoAdminRouter(BaseRouter[AppContext]):
    handlers = (
        CreatePromoHandler,
        PromoCardHandler,
        PromoCatalogHandler,
        PromoCardPressHandler,
        PromoCatalogPressHandler,
    )


__all__ = ["PromoAdminRouter"]
