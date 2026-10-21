from typing import Any

from selfrot import CallbackPayload, CommandArgs, MessageHandler, View, ViewContent, button
from selfrot.context import BaseContext
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import (
    InlineKeyboardButton,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.database.models import PromoCode

from ....context import AppContext
from ...rich import table_cell
from ...types import DataMessageCallbackQuery, TextUserMessage
from .catalog import PromoCatalog
from .dates import moscow_time
from .payloads import PromoCardPress
from .view import (
    PHRASES,
    activations_text,
    app_context,
    rewards_text,
    status_text,
    term_line,
)


class PromoCardArgs(CommandArgs):
    name: str


CARD_COMMAND = Command("promo", PromoCardArgs)


class PromoCard(View):
    payload = PromoCardPress

    @classmethod
    async def render(cls, ctx: BaseContext[Any], data: CallbackPayload | None) -> ViewContent:
        app = app_context(ctx)
        if isinstance(data, PromoCardPress):
            promo = await app.promo_service.get(data.promo_id)
            press = data
        else:
            # Первый показ — по команде /promo <название>, а не по кнопке.
            name = CARD_COMMAND.parse(app).name
            promo = await app.promo_service.find(name)
            if promo is None:
                return ViewContent(body=app.text(PHRASES.card.not_found(name=name)))
            press = PromoCardPress(promo_id=promo.id)

        if promo is None:
            return ViewContent(body=app.text(PHRASES.card.gone()))
        confirming = press.action == "delete" and promo.deleted_at is None
        return ViewContent(
            body=await cls.rich(app, promo, confirming),
            rows=cls.buttons(app, promo, press.page, confirming),
        )

    @classmethod
    async def apply(cls, ctx: BaseContext[Any], data: CallbackPayload) -> None:
        app = app_context(ctx)
        assert isinstance(data, PromoCardPress)
        if data.action == "confirm":
            await app.promo_service.delete(data.promo_id, app.callback_query.user.id)

    @classmethod
    async def rich(cls, ctx: AppContext[Any], promo: PromoCode, confirming: bool) -> InputRichMessage:
        card = PHRASES.card
        names = await ctx.first_names([promo.created_by, *filter(None, [promo.deleted_by])])

        def when_who(at: Any, who: int) -> str:
            return ctx.text(card.who_when(date=moscow_time(at), who=names.get(who, str(who))))

        rows = [
            (card.status(), status_text(ctx, promo)),
            (card.rewards(), rewards_text(ctx, promo)),
            (card.activations(), activations_text(ctx, promo)),
            (card.term(), ctx.text(term_line(promo))),
            (card.created(), when_who(promo.created_at, promo.created_by)),
        ]
        if promo.deleted_at is not None and promo.deleted_by is not None:
            rows.append((card.deleted(), when_who(promo.deleted_at, promo.deleted_by)))

        header = [
            table_cell(ctx.text(card.column_field()), header=True),
            table_cell(ctx.text(card.column_value()), header=True),
        ]
        cells = [header, *([table_cell(ctx.text(label)), table_cell(value)] for label, value in rows)]
        blocks: list[Any] = [
            InputRichBlockSectionHeading(text=ctx.text(card.title(name=promo.name)), size=3),
            InputRichBlockTable(cells=cells, is_bordered=True, is_striped=True),
        ]
        if confirming:
            blocks.append(InputRichBlockParagraph(text=ctx.text(card.confirm_question())))
        return InputRichMessage(blocks=blocks)

    @classmethod
    def buttons(
        cls, ctx: AppContext[Any], promo: PromoCode, page: int, confirming: bool
    ) -> list[list[InlineKeyboardButton]]:
        card = PHRASES.card

        def press(action: Any) -> PromoCardPress:
            return PromoCardPress(promo_id=promo.id, action=action, page=page)

        back = button(ctx.text(card.back_button()), PromoCatalog.payload(page=page))  # type: ignore[call-arg]
        if confirming:
            return [
                [
                    button(ctx.text(card.confirm_button()), press("confirm")),
                    button(ctx.text(card.cancel_button()), press("cancel")),
                ]
            ]
        if promo.deleted_at is None:
            return [[button(ctx.text(card.delete_button()), press("delete"))], [back]]
        return [[back]]


class PromoCardHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = CARD_COMMAND & HasUser()
    usage = PHRASES.card.usage()

    async def handle(self) -> None:
        await PromoCard.show(self.ctx)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.usage, reply=True)
            return
        raise exc


class PromoCardPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = PromoCard.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        await PromoCard.press(self.ctx)
