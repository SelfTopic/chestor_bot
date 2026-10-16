from typing import Any

from selfrot import MessageHandler, Pagination, ViewContent, button
from selfrot.context import BaseContext
from selfrot.filter import Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import (
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.database.models import PromoCode

from ....context import AppContext
from ...rich import table_cell
from ...types import DataMessageCallbackQuery, TextUserMessage
from .dates import moscow_time
from .payloads import PromoCardPress
from .view import PHRASES, activations_text, app_context, status_text

BUTTONS_PER_ROW = 2


class PromoCatalog(Pagination, prefix="promos"):
    per_page = 8

    @classmethod
    async def total(cls, ctx: BaseContext[Any]) -> int:
        return await app_context(ctx).promo_service.count()

    @classmethod
    async def page_content(cls, ctx: BaseContext[Any], page: int) -> ViewContent:
        app = app_context(ctx)
        promos = await app.promo_service.page(page, cls.per_page)
        catalog = PHRASES.catalog
        heading = InputRichBlockSectionHeading(text=app.text(catalog.title()), size=3)
        if not promos:
            empty = InputRichBlockParagraph(text=app.text(catalog.empty()))
            return ViewContent(body=InputRichMessage(blocks=[heading, empty]))

        header = [
            table_cell(app.text(column()), header=True)
            for column in (
                catalog.column_name,
                catalog.column_status,
                catalog.column_activations,
                catalog.column_term,
            )
        ]
        cells = [header, *(cls.row(app, promo) for promo in promos)]
        table = InputRichBlockTable(cells=cells, is_bordered=True, is_striped=True)

        buttons = [button(promo.name, PromoCardPress(promo_id=promo.id, page=page)) for promo in promos]
        rows = [buttons[i : i + BUTTONS_PER_ROW] for i in range(0, len(buttons), BUTTONS_PER_ROW)]
        return ViewContent(body=InputRichMessage(blocks=[heading, table]), rows=rows)

    @classmethod
    def row(cls, ctx: AppContext[Any], promo: PromoCode) -> list[Any]:
        if promo.expires_at is None:
            term = ctx.text(PHRASES.forever())
        else:
            term = ctx.text(PHRASES.catalog.term_until(date=moscow_time(promo.expires_at)))
        return [
            table_cell(promo.name),
            table_cell(status_text(ctx, promo)),
            table_cell(activations_text(ctx, promo)),
            table_cell(term),
        ]


class PromoCatalogHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Command("promos") & HasUser()

    async def handle(self) -> None:
        await PromoCatalog.show(self.ctx)


class PromoCatalogPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = PromoCatalog.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        await PromoCatalog.press(self.ctx)
