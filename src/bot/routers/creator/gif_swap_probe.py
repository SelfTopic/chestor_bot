import asyncio
import io
import math
import random
import time

from PIL import Image, ImageDraw, ImageFont
from selfrot import BaseRouter, CallbackPayload, InlineKeyboard, MessageHandler, button
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import Command, HasMessageCallbackQuery
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import (
    InputFile,
    InputMediaAnimation,
    InputMediaPhoto,
    InputRichBlockAnimation,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichMessage,
    Message,
)

from ...context import AppContext
from ..types import DataMessageCallbackQuery, TextMessage

WIDTH, HEIGHT, FRAMES = 480, 270, 48

# message_id автомата → file_id двух гифок; проба живёт только в памяти процесса.
probes: dict[int, tuple[str, str]] = {}


class SwapPress(CallbackPayload, prefix="gif_probe"):
    show: int


def chart_gif(crash: bool) -> bytes:
    frames = []
    for frame in range(FRAMES):
        image = Image.new("RGB", (WIDTH, HEIGHT), (18, 18, 24))
        draw = ImageDraw.Draw(image)
        points = []
        for step in range(frame + 1):
            x = 20 + step * (WIDTH - 40) / FRAMES
            y = HEIGHT - 20 - (math.exp(step / 14) - 1) * 12
            points.append((x, max(y, 20)))
        if crash and frame > FRAMES * 2 // 3:
            points.append((points[-1][0] + 8, HEIGHT - 20))
        color = (230, 60, 60) if crash and frame > FRAMES * 2 // 3 else (60, 220, 120)
        if len(points) > 1:
            draw.line(points, fill=color, width=4)
        multiplier = math.exp(frame / 14)
        draw.text((20, 16), f"x{multiplier:.2f}", fill=(240, 240, 240))
        frames.append(image)

    buffer = io.BytesIO()
    frames[0].save(
        buffer, "GIF", save_all=True, append_images=frames[1:], duration=80, loop=0
    )
    return buffer.getvalue()


def history_strip() -> bytes:
    font = ImageFont.truetype("src/assets/fonts/Rubik.ttf", 38)
    font.set_variation_by_name(b"SemiBold")
    image = Image.new("RGB", (1920, 168), (14, 10, 34))
    draw = ImageDraw.Draw(image)
    x = 32
    for age in range(12):
        multiplier = max(1.0, 0.96 / (1 - random.random()))
        if multiplier < 1.01:
            color = (255, 72, 96)
        elif multiplier < 2:
            color = (98, 132, 255)
        elif multiplier < 10:
            color = (168, 98, 255)
        else:
            color = (255, 186, 64)
        fade = max(0.35, 1 - age * 0.07)
        color = tuple(int(14 + (part - 14) * fade) for part in color)
        label = f"x{multiplier:.2f}"
        width = draw.textlength(label, font=font) + 60
        if x + width > 1888:
            break
        draw.rounded_rectangle([x, 40, x + width, 128], radius=20, fill=color)
        draw.text((x + width / 2, 84), label, font=font, fill=(255, 255, 255), anchor="mm")
        x += width + 20

    buffer = io.BytesIO()
    image.resize((960, 84), Image.Resampling.LANCZOS).save(buffer, "PNG")
    return buffer.getvalue()


def probe_message(file_id: str, note: str) -> InputRichMessage:
    return InputRichMessage(
        blocks=[
            InputRichBlockPhoto(
                photo=InputMediaPhoto(media=InputFile(history_strip(), "history.png"))
            ),
            InputRichBlockAnimation(animation=InputMediaAnimation(media=file_id)),
            InputRichBlockParagraph(text=note),
        ]
    )


def swap_keyboard(show: int):
    return InlineKeyboard().row(button("swap gif", SwapPress(show=show))).markup()


class GifSwapProbeHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("probe_gif")

    async def handle(self) -> None:
        message = self.ctx.message
        file_ids = []
        for crash in (False, True):
            sent = await message.answer_animation(
                animation=InputFile(
                    await asyncio.to_thread(chart_gif, crash), f"chart_{crash}.gif"
                )
            )
            assert sent.animation is not None
            file_ids.append(sent.animation.file_id)
            await sent.delete()

        growth, crashed = file_ids
        machine = await message.reply_rich_message(
            rich_message=probe_message(growth, "growth gif, press to swap"),
            reply_markup=swap_keyboard(1),
        )
        probes[machine.message_id] = (growth, crashed)


class GifSwapPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = SwapPress.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        message = callback.message
        if not isinstance(message, Message) or message.message_id not in probes:
            await callback.answer("probe expired", show_alert=True)
            return

        show = SwapPress.unpack(callback.data).show
        file_id = probes[message.message_id][show]
        started = time.monotonic()
        try:
            await message.edit_text(
                rich_message=probe_message(file_id, f"now showing gif #{show}"),
                reply_markup=swap_keyboard(1 - show),
            )
        except TelegramAPIError as error:
            await callback.answer(f"edit failed: {error}"[:200], show_alert=True)
            return
        await callback.answer(f"edited in {time.monotonic() - started:.2f} s")


class GifSwapProbeRouter(BaseRouter[AppContext]):
    handlers = (GifSwapProbeHandler, GifSwapPressHandler)
