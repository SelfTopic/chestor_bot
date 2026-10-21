from collections.abc import Callable
from typing import Any, Literal

from selfrot import CallbackPayload, button
from selfrot.types import (
    InlineKeyboardButton,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.bot.dialogs import Dialogs, Line
from src.bot.services.moderation import MAX_WARN_LIMIT, MIN_WARN_LIMIT
from src.bot.types import ChatModeration, ModerationFeature, ModerationVoice, WarnPenalty

from ....context import AppContext
from ...rich import table_cell
from ..flow import expiry_text, term_text
from .warns import penalty_text

MENU = Dialogs.moderation.menu

# Любой другой срок задаётся командой; кнопки листают этот ряд по кругу.
TERM_PRESETS: tuple[int | None, ...] = (
    60,
    300,
    900,
    1800,
    3600,
    10800,
    43200,
    86400,
    604800,
    2592000,
    None,
)

MenuAction = Literal["toggle", "term", "limit", "penalty", "voice", "noop"]
TermKey = Literal["mute", "ban", "penalty", "expiry"]


class MenuPress(CallbackPayload, prefix="modmenu"):
    action: MenuAction
    key: str = ""
    step: int = 0


FEATURE_LABELS: dict[ModerationFeature, Callable[[], Line]] = {
    ModerationFeature.MUTE: MENU.mute,
    ModerationFeature.BAN: MENU.ban,
    ModerationFeature.KICK: MENU.kick,
    ModerationFeature.WARNS: MENU.warns,
    ModerationFeature.NOTICES: MENU.notices,
}

TERM_LABELS: dict[TermKey, Callable[[], Line]] = {
    "mute": MENU.mute_default,
    "ban": MENU.ban_default,
    "penalty": MENU.warn_penalty,
    "expiry": MENU.warn_expiry,
}

PENALTY_ORDER = (WarnPenalty.MUTE, WarnPenalty.BAN, WarnPenalty.KICK)


def shift_term(current: int | None, step: int) -> int | None:
    if current in TERM_PRESETS:
        return TERM_PRESETS[(TERM_PRESETS.index(current) + step) % len(TERM_PRESETS)]

    # Срок, заданный командой, вне ряда: шаг ведёт к ближайшему значению ряда.
    finite = [preset for preset in TERM_PRESETS if preset is not None]
    assert current is not None
    if step > 0:
        return next((preset for preset in finite if preset > current), None)
    smaller = [preset for preset in finite if preset < current]
    return smaller[-1] if smaller else None


def term_key(key: str) -> TermKey | None:
    match key:
        case "mute" | "ban" | "penalty" | "expiry":
            return key
        case _:
            return None


def term_seconds(settings: ChatModeration, key: TermKey) -> int | None:
    return {
        "mute": settings.mute_default_seconds,
        "ban": settings.ban_default_seconds,
        "penalty": settings.warn_penalty_seconds,
        "expiry": settings.warn_expiry_seconds,
    }[key]


def next_penalty(penalty: WarnPenalty) -> WarnPenalty:
    return PENALTY_ORDER[(PENALTY_ORDER.index(penalty) + 1) % len(PENALTY_ORDER)]


def switch_text(ctx: AppContext[Any], enabled: bool) -> str:
    return ctx.text(MENU.on() if enabled else MENU.off())


def voice_text(ctx: AppContext[Any], voice: ModerationVoice) -> str:
    return ctx.text(MENU.voice_rough() if voice is ModerationVoice.ROUGH else MENU.voice_neutral())


class MenuTable:
    def __init__(
        self,
        ctx: AppContext[Any],
        settings: ChatModeration,
        chat_title: str,
        admin_chat_title: str | None,
    ) -> None:
        self.ctx = ctx
        self.settings = settings
        self.chat_title = chat_title
        self.admin_chat_title = admin_chat_title

    def term(self, key: TermKey) -> str:
        seconds = term_seconds(self.settings, key)
        if key == "expiry":
            return expiry_text(self.ctx, seconds)
        if key == "penalty":
            return penalty_text(self.ctx, self.settings.warn_penalty, seconds)
        return term_text(self.ctx, seconds)

    def rows(self) -> list[tuple[str, str]]:
        ctx, settings = self.ctx, self.settings
        rows = [
            (ctx.text(label()), switch_text(ctx, settings.enabled(feature)))
            for feature, label in FEATURE_LABELS.items()
        ]
        rows += [
            (ctx.text(MENU.mute_default()), self.term("mute")),
            (ctx.text(MENU.ban_default()), self.term("ban")),
            (ctx.text(MENU.warn_limit()), str(settings.warn_limit)),
            (ctx.text(MENU.warn_penalty()), self.term("penalty")),
            (ctx.text(MENU.warn_expiry()), self.term("expiry")),
            (ctx.text(MENU.voice()), voice_text(ctx, settings.voice)),
            (
                ctx.text(MENU.admin_chat()),
                self.admin_chat_title or ctx.text(MENU.admin_chat_none()),
            ),
        ]
        return rows

    def rich(self) -> InputRichMessage:
        ctx = self.ctx
        header = [
            table_cell(ctx.text(MENU.column_setting()), header=True),
            table_cell(ctx.text(MENU.column_value()), header=True),
        ]
        cells = [header, *([table_cell(name), table_cell(value)] for name, value in self.rows())]
        return InputRichMessage(
            blocks=[
                InputRichBlockSectionHeading(
                    text=ctx.text(MENU.title(chat=self.chat_title)), size=3
                ),
                InputRichBlockTable(cells=cells, is_bordered=True, is_striped=True),
                InputRichBlockParagraph(text=ctx.text(MENU.hint())),
            ]
        )

    def buttons(self) -> list[list[InlineKeyboardButton]]:
        ctx, settings = self.ctx, self.settings

        def toggle(feature: ModerationFeature) -> InlineKeyboardButton:
            name = ctx.text(FEATURE_LABELS[feature]())
            label = MENU.button_on(name=name) if settings.enabled(feature) else MENU.button_off(name=name)
            return button(ctx.text(label), MenuPress(action="toggle", key=feature.value))

        def step(action: MenuAction, key: str, step: int, label: Line) -> InlineKeyboardButton:
            return button(ctx.text(label), MenuPress(action=action, key=key, step=step))

        # Шаг за край лимита ничего бы не поменял, а правку без изменений Telegram отвергает.
        def edge() -> InlineKeyboardButton:
            return button(" ", MenuPress(action="noop", key="edge"))

        def middle(label: Line) -> InlineKeyboardButton:
            return button(ctx.text(label), MenuPress(action="noop"))

        rows = [
            [toggle(f) for f in (ModerationFeature.MUTE, ModerationFeature.BAN, ModerationFeature.KICK)],
            [toggle(ModerationFeature.WARNS), toggle(ModerationFeature.NOTICES)],
        ]
        for key, title in TERM_LABELS.items():
            label = MENU.button_value(name=ctx.text(title()), value=self.term(key))
            rows.append(
                [
                    step("term", key, -1, MENU.button_prev()),
                    middle(label),
                    step("term", key, 1, MENU.button_next()),
                ]
            )

        limit = settings.warn_limit
        rows.append(
            [
                step("limit", "", -1, MENU.button_minus()) if limit > MIN_WARN_LIMIT else edge(),
                middle(MENU.button_value(name=ctx.text(MENU.warn_limit()), value=limit)),
                step("limit", "", 1, MENU.button_plus()) if limit < MAX_WARN_LIMIT else edge(),
            ]
        )

        penalty = MENU.button_value(name=ctx.text(MENU.warn_penalty()), value=self.term("penalty"))
        rows.append([button(ctx.text(penalty), MenuPress(action="penalty"))])
        voice = MENU.button_value(name=ctx.text(MENU.voice()), value=voice_text(ctx, settings.voice))
        rows.append([button(ctx.text(voice), MenuPress(action="voice"))])
        return rows
