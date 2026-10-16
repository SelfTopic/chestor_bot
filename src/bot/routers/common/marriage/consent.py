import logging

from selfrot import InlineKeyboard, MessageHandler, button
from selfrot.filter import Command, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from src.bot.dialogs import Line
from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.services.family import ConsentRefusal, ConsentRefused, ProposalState

from ....context import AppContext
from ...types import UserMessage
from ...utils import quiet_edit
from .payloads import DivorcePress, MarriageAnswer, MarryLink, ProposalPayment
from .render import PHRASES, mentions, proposal_view

logger = logging.getLogger(__name__)


def refusal_line(reason: ConsentRefusal) -> Line:
    consent = PHRASES.consent
    match reason:
        case ConsentRefusal.STALE:
            return consent.stale()
        case ConsentRefusal.NOT_INVITED:
            return consent.not_invited()
        case ConsentRefusal.ALREADY_CONSENTED:
            return consent.already()
        case ConsentRefusal.NOT_ENOUGH_MONEY:
            return consent.not_enough_money(price=MARRIAGE_CONFIG.acceptance_price)


class ProposalAnswerHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    agreed = MarriageAnswer.filter(answer="agree").pressed_by("expected_id")
    declined = MarriageAnswer.filter(answer="decline").pressed_by("expected_id")

    @agreed
    async def agree(self) -> None:
        payload = self.agreed.parse(self.ctx)
        try:
            state = await self.ctx.family_service.consent(
                payload.proposal_id, payload.expected_id
            )
        except ConsentRefused as refused:
            await self.refuse(refused)
            return

        done = PHRASES.consent.married() if state.married else PHRASES.consent.accepted()
        await self.show(state, PHRASES.family_voted(), done)

    @declined
    async def decline(self) -> None:
        payload = self.declined.parse(self.ctx)
        try:
            state = await self.ctx.family_service.decline(
                payload.proposal_id, payload.expected_id
            )
        except ConsentRefused as refused:
            await self.refuse(refused)
            return

        await self.show(state, PHRASES.family_declined(), PHRASES.consent.declined())

    async def refuse(self, refused: ConsentRefused) -> None:
        await self.ctx.callback_query.answer(
            self.ctx.text(refusal_line(refused.reason)), show_alert=True
        )

    async def show(self, state: ProposalState, private_line: Line, alert: Line) -> None:
        await self.refresh_invite(state)
        message = self.ctx.callback_query.message
        # Член семьи отвечает в личке: там правится его сообщение, а приглашение — в группе.
        if isinstance(message, Message) and message.message_id != state.proposal.message_id:
            with quiet_edit("marriage private answer"):
                await message.edit_text(self.ctx.text(private_line))
        await self.ctx.callback_query.answer(self.ctx.text(alert))

    async def refresh_invite(self, state: ProposalState) -> None:
        proposal = state.proposal
        if proposal.message_id is None:
            return
        text, keyboard = await proposal_view(self.ctx, state, self.ctx.bot)
        with quiet_edit("marriage invite"):
            await self.ctx.bot.edit_message_text(
                chat_id=proposal.chat_id,
                message_id=proposal.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )


class FamilyConsentLinkHandler(MessageHandler[AppContext[UserMessage]]):
    link = Command("start", MarryLink, deep_link=True)
    query = link & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        member_id = ctx.message.user.id
        state = await ctx.family_service.state(self.link.parse(ctx).proposal_id)
        if state is None or state.proposal.stage != "awaiting":
            await ctx.say(PHRASES.link_stale())
            return
        if member_id not in state.family_members:
            await ctx.say(PHRASES.link_not_family())
            return

        proposer, target = state.required[:2]
        who = await mentions(ctx, (proposer, target))
        vote = PHRASES.family_vote(proposer=who[proposer], target=who[target])
        proposal_id = state.proposal.id
        keyboard = InlineKeyboard().row(
            button(
                ctx.text(PHRASES.buttons.family_vote()),
                MarriageAnswer(proposal_id=proposal_id, expected_id=member_id, answer="agree"),
            ),
            button(
                ctx.text(PHRASES.buttons.family_decline()),
                MarriageAnswer(proposal_id=proposal_id, expected_id=member_id, answer="decline"),
            ),
        )
        await ctx.message.answer(ctx.text(vote), reply_markup=keyboard.markup(), parse_mode="HTML")


class NotYourMarriageButtonHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = ProposalPayment.filter() | MarriageAnswer.filter() | DivorcePress.filter()

    async def handle(self) -> None:
        await self.ctx.callback_query.answer(
            self.ctx.text(PHRASES.not_your_button()), show_alert=True
        )
