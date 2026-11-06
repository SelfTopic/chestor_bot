import asyncio

from selfrot import Bot, InlineKeyboard, button
from selfrot.exceptions import TelegramBadRequest
from selfrot.types import InlineKeyboardMarkup, InputRichBlockParagraph, InputRichMessage, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs, Line, LineText
from src.bot.dialogs.vocab import DEP_COLOR_NAMES
from src.bot.exceptions import RouletteStaleMedia
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.repositories import ChatRepository, UserRepository
from src.bot.repositories.user_names import UserNameRepository
from src.bot.services.dialog import DialogService
from src.bot.services.language import LanguageService
from src.bot.services.roulette import Choice, Outcome, Screen, Shown, Stage, closed_picture
from src.bot.types.dep import DepColor
from src.bot.utils import format_amount

from ..media import animation_file_id, media_block, stored
from .payloads import AmountPress, ColorPress, HintPress, SpinPress

ROULETTE = Dialogs.roulette
# Кнопки цветов идут по возрастанию коэффициента; в callback — номер цвета в этом списке.
COLORS = (DepColor.RED, DepColor.BLUE, DepColor.GREEN, DepColor.YELLOW, DepColor.WHITE)
EMOJI = {
    DepColor.RED: "🔴",
    DepColor.BLUE: "🔵",
    DepColor.GREEN: "🟢",
    DepColor.YELLOW: "🟡",
    DepColor.WHITE: "⚪",
}
# Цвет кнопки в Telegram бывает только красным, синим и зелёным.
STYLES = {DepColor.RED: "danger", DepColor.BLUE: "primary", DepColor.GREEN: "success"}


def multiplier(color: DepColor) -> str:
    return f"{LOTTERY_CONFIG.get_multiplier(color.value):g}"


def color_name(text: LineText, color: DepColor) -> str:
    return f"{EMOJI[color]} {text(DEP_COLOR_NAMES[color])}"


def keyboard(screen: Screen, text: LineText) -> InlineKeyboardMarkup | None:
    if screen.stage is Stage.CLOSED:
        return None
    board = InlineKeyboard()
    board.row(
        button(text(ROULETTE.color_header()), HintPress(color=True)),
        button(text(ROULETTE.amount_header()), HintPress(color=False)),
    )
    chosen = screen.choice
    for index, (color, amount) in enumerate(zip(COLORS, LOTTERY_CONFIG.bet_buttons, strict=True)):
        name, ratio = text(DEP_COLOR_NAMES[color]), multiplier(color)
        color_line = (
            ROULETTE.color_button_chosen(color=name, multiplier=ratio)
            if color is chosen.color
            else ROULETTE.color_button(emoji=EMOJI[color], color=name, multiplier=ratio)
        )
        shown = format_amount(amount)
        amount_line = (
            ROULETTE.amount_button_chosen(amount=shown)
            if amount == chosen.amount
            else ROULETTE.amount_button(amount=shown)
        )
        style = {"style": STYLES[color]} if color in STYLES else {}
        board.row(
            button(text(color_line), ColorPress(machine=screen.machine_id, color=index), **style),
            button(text(amount_line), AmountPress(machine=screen.machine_id, amount=amount)),
        )
    board.row(button(text(ROULETTE.spin_button()), SpinPress(machine=screen.machine_id)))
    return board.markup()


class TelegramRouletteScreen:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        dialog_service: DialogService,
    ) -> None:
        self._bot = bot
        self._session_factory = session_factory
        self._dialog_service = dialog_service

    async def show(self, screen: Screen) -> Shown:
        text, name = await self._context(screen.chat_id, screen.user_id)
        paragraph = "\n".join(text(line) for line in self._lines(screen, name, text))
        rich = InputRichMessage(
            blocks=[media_block(screen.media), InputRichBlockParagraph(text=paragraph)]
        )
        markup = keyboard(screen, text)
        try:
            if screen.message_id is None:
                message = await self._bot.send_rich_message(
                    screen.chat_id, rich, reply_markup=markup
                )
            else:
                edited = await self._bot.edit_message_text(
                    chat_id=screen.chat_id,
                    message_id=screen.message_id,
                    rich_message=rich,
                    reply_markup=markup,
                )
                message = edited if isinstance(edited, Message) else None
        except TelegramBadRequest:
            if stored(screen.media):
                raise RouletteStaleMedia() from None
            raise
        message_id = message.message_id if message is not None else screen.message_id
        assert message_id is not None
        return Shown(message_id, animation_file_id(message))

    async def closed_picture(self, chat_id: int, position: int) -> bytes:
        async with self._session_factory() as session:
            text = await self._languages(session).text_for(chat_id)
        return await asyncio.to_thread(
            closed_picture, position, text(ROULETTE.closed_title()), text(ROULETTE.closed_hint())
        )

    def _languages(self, session: AsyncSession) -> LanguageService:
        return LanguageService(UserRepository(session), ChatRepository(session), self._dialog_service)

    async def _context(self, chat_id: int, user_id: int) -> tuple[LineText, str]:
        async with self._session_factory() as session:
            text = await self._languages(session).text_for(chat_id)
            names = await UserNameRepository(session).names([user_id], chat_id)
        return text, names.get(user_id, str(user_id))

    def _lines(self, screen: Screen, name: str, text: LineText) -> list[Line]:
        lines: list[Line] = [ROULETTE.title(name=name)]
        if screen.stage is Stage.CLOSED:
            return [*lines, ROULETTE.closed()]
        if screen.stage is Stage.SPINNING:
            choice = screen.outcome
            assert choice is not None
            spun = color_name(text, choice.color)
            return [*lines, ROULETTE.spinning(color=spun, amount=format_amount(choice.bet))]
        if screen.outcome is not None:
            lines.append(self._outcome(screen.outcome, text))
        lines.append(self._choice(screen.choice, text))
        lines.append(ROULETTE.balance(balance=format_amount(screen.balance)))
        return lines

    @staticmethod
    def _outcome(outcome: Outcome, text: LineText) -> Line:
        winning = color_name(text, outcome.winning)
        if outcome.won:
            return ROULETTE.won(winning=winning, earned=format_amount(outcome.earned))
        return ROULETTE.lost(winning=winning, bet=format_amount(outcome.bet))

    @staticmethod
    def _choice(choice: Choice, text: LineText) -> Line:
        if choice.color is not None and choice.amount is not None:
            return ROULETTE.choice(
                color=color_name(text, choice.color),
                multiplier=multiplier(choice.color),
                amount=format_amount(choice.amount),
            )
        if choice.amount is not None:
            return ROULETTE.choose_color(amount=format_amount(choice.amount))
        if choice.color is not None:
            return ROULETTE.choose_amount(color=color_name(text, choice.color))
        return ROULETTE.choose()
