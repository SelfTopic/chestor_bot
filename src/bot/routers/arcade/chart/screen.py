import asyncio

from selfrot import Bot, InlineKeyboard, button
from selfrot.exceptions import TelegramBadRequest
from selfrot.types import (
    InlineKeyboardMarkup,
    InputFile,
    InputMediaAnimation,
    InputMediaPhoto,
    InputRichBlockAnimation,
    InputRichBlockParagraph,
    InputRichBlock,
    InputRichBlockPhoto,
    InputRichMessage,
    Message,
    RichBlockAnimation,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs, Line, LineText
from src.bot.exceptions import ChartStaleVideo
from src.bot.game_configs import CHART_CONFIG
from src.bot.repositories import ChatRepository, UserRepository
from src.bot.repositories.user_names import UserNameRepository
from src.bot.services.chart_game import (
    BetLine,
    Media,
    PanelRow,
    Picture,
    Screen,
    Shown,
    Stage,
    StoredPicture,
    StoredVideo,
    VideoFile,
    bets_panel,
)
from src.bot.services.dialog import DialogService
from src.bot.services.language import LanguageService
from src.bot.utils import format_amount

from .payloads import BetPress, CashOutPress, HintPress, TargetPress

CHART = Dialogs.chart

def multiplier(cents: int) -> str:
    return f"{cents / 100:.2f}"


def media_block(media: Media) -> InputRichBlockPhoto | InputRichBlockAnimation:
    match media:
        case Picture(png=png):
            return InputRichBlockPhoto(photo=InputMediaPhoto(media=InputFile(png, "chart.png")))
        case VideoFile(path=path):
            return InputRichBlockAnimation(
                animation=InputMediaAnimation(media=InputFile.from_path(path))
            )
        case StoredVideo(file_id=file_id):
            return InputRichBlockAnimation(animation=InputMediaAnimation(media=file_id))
        case StoredPicture(file_id=file_id):
            return InputRichBlockPhoto(photo=InputMediaPhoto(media=file_id))


def stored(media: Media | None) -> bool:
    return isinstance(media, (StoredVideo, StoredPicture))


def keyboard(stage: Stage, text: LineText) -> InlineKeyboardMarkup:
    board = InlineKeyboard()
    if stage is Stage.PREPARATION:
        board.row(
            button(text(CHART.bet_header()), HintPress(target=False)),
            button(text(CHART.target_header()), HintPress(target=True)),
        )
        for amount, target in zip(CHART_CONFIG.bet_buttons, CHART_CONFIG.target_buttons, strict=True):
            board.row(
                button(text(CHART.amount_button(amount=format_amount(amount))), BetPress(amount=amount)),
                button(text(CHART.target_button(target=f"{target / 100:g}")), TargetPress(target=target)),
            )
    elif stage is Stage.GROWTH:
        board.row(button(text(CHART.cash_out_button()), CashOutPress()))
    return board.markup()


def animation_file_id(message: Message | None) -> str | None:
    if message is None or message.rich_message is None:
        return None
    for block in message.rich_message.blocks:
        if isinstance(block, RichBlockAnimation):
            return block.animation.file_id
    return None


class TelegramMachineScreen:
    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        dialog_service: DialogService,
    ) -> None:
        self._bot = bot
        self._session_factory = session_factory
        self._dialog_service = dialog_service
        # Язык и имена берутся из базы раз на автомат: правка в момент обвала её не ждёт.
        self._texts: dict[int, LineText] = {}
        self._names: dict[int, dict[int, str]] = {}

    async def show(self, screen: Screen) -> Shown:
        text, names = await self._context(screen)
        if screen.stage in (Stage.CLOSED, Stage.ABANDONED):
            self._texts.pop(screen.chat_id, None)
            self._names.pop(screen.chat_id, None)
        rich = InputRichMessage(blocks=self._blocks(screen, text, names))
        markup = keyboard(screen.stage, text)
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
            if stored(screen.media) or stored(screen.history) or stored(screen.panel):
                raise ChartStaleVideo() from None
            raise
        message_id = message.message_id if message is not None else screen.message_id
        assert message_id is not None
        return Shown(message_id, animation_file_id(message))

    async def bets_picture(self, chat_id: int, bets: list[BetLine]) -> bytes:
        text, names = await self._lookup(chat_id, bets)
        async with self._session_factory() as session:
            usernames = await UserNameRepository(session).usernames([bet.telegram_id for bet in bets])
        rows = [
            PanelRow(
                names.get(bet.telegram_id, str(bet.telegram_id)),
                format_amount(bet.amount),
                None if bet.target is None else text(CHART.panel_target(target=multiplier(bet.target))),
                bet.target,
                usernames.get(bet.telegram_id),
            )
            for bet in bets
        ]
        bank = text(CHART.panel_bank(amount=format_amount(sum(bet.amount for bet in bets))))
        return await asyncio.to_thread(bets_panel, text(CHART.panel_title()), bank, rows)

    async def _context(self, screen: Screen) -> tuple[LineText, dict[int, str]]:
        return await self._lookup(screen.chat_id, screen.bets)

    async def _lookup(self, chat_id: int, bets: list[BetLine]) -> tuple[LineText, dict[int, str]]:
        names = self._names.setdefault(chat_id, {})
        missing = [bet.telegram_id for bet in bets if bet.telegram_id not in names]
        text = self._texts.get(chat_id)
        if text is not None and not missing:
            return text, names
        async with self._session_factory() as session:
            if text is None:
                languages = LanguageService(
                    UserRepository(session), ChatRepository(session), self._dialog_service
                )
                text = self._texts[chat_id] = await languages.text_for(chat_id)
            names.update(await UserNameRepository(session).names(missing, chat_id))
        return text, names

    def _blocks(self, screen: Screen, text: LineText, names: dict[int, str]) -> list[InputRichBlock]:
        blocks: list[InputRichBlock] = []
        if screen.history is not None:
            blocks.append(media_block(screen.history))
        blocks.append(media_block(screen.media))
        if screen.panel is not None:
            blocks.append(media_block(screen.panel))
        blocks.append(InputRichBlockParagraph(text="\n".join(text(line) for line in self._headline(screen))))
        # В росте ставки на картинке панели; текстом — если панель не подготовилась.
        shown_on_panel = screen.stage is Stage.GROWTH and screen.panel is not None
        bets = [] if shown_on_panel else screen.bets
        lines = [text(self._bet_line(screen.stage, bet, names)) for bet in bets]
        # Не сворачиваемым блоком: правка сообщения каждый раз сворачивает его заново.
        if lines:
            summary = text(CHART.bets(count=len(lines)))
            blocks.append(InputRichBlockParagraph(text="\n".join([summary, *lines])))
        elif screen.stage is Stage.GROWTH and not screen.bets:
            blocks.append(InputRichBlockParagraph(text=text(CHART.no_bets())))
        return blocks

    @staticmethod
    def _headline(screen: Screen) -> list[Line]:
        lines: list[Line] = []
        if screen.crash is not None and screen.stage in (Stage.PREPARATION, Stage.CLOSED):
            crash = multiplier(screen.crash)
            capped = screen.crash == CHART_CONFIG.max_cents
            lines.append(CHART.capped(crash=crash) if capped else CHART.crashed(crash=crash))
        match screen.stage:
            case Stage.PREPARATION:
                minutes = max(1, round(screen.closes_in / 60))
                lines.append(CHART.preparation(minutes=minutes))
            case Stage.GROWTH:
                lines.append(CHART.growth())
            case Stage.CLOSED:
                lines.append(CHART.closed())
            case Stage.ABANDONED:
                lines.append(CHART.abandoned())
        return lines

    @staticmethod
    def _bet_line(stage: Stage, bet: BetLine, names: dict[int, str]) -> Line:
        name = names.get(bet.telegram_id, str(bet.telegram_id))
        amount = format_amount(bet.amount)
        if stage is Stage.ABANDONED:
            return CHART.refunded_line(name=name, amount=amount)
        if stage is Stage.GROWTH:
            if bet.target is None:
                return CHART.bet_line(name=name, amount=amount)
            return CHART.bet_line_target(name=name, amount=amount, target=multiplier(bet.target))
        if bet.cashed_at is not None:
            return CHART.won_line(
                name=name, multiplier=multiplier(bet.cashed_at), payout=format_amount(bet.payout)
            )
        return CHART.lost_line(name=name, amount=amount)
