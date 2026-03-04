import logging
from pathlib import Path
from typing import Iterator, List

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.bot.services.battle.animation_loader import (
    get_animation_path,
    get_clip_frame,
)
from src.bot.services.battle.models import TimelineEvent
from src.bot.services.battle.renderer import (
    BG_COLOR,
    DMG_Y,
    FONT_CYR,
    FONT_MONO,
    H,
    W,
    draw_action_overlay,
    draw_damage_number,
    draw_event_label,
    make_base_frame,
)
from src.bot.services.battle.sprite_animator import animate_idle
from src.bot.services.battle.sprites import get_sprite

logger = logging.getLogger(__name__)
FPS = 24


class BattleVideoGenerator:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # MAIN ENTRY
    # ======================================================

    def generate_timeline(
        self,
        timeline: List[TimelineEvent],
        output_path: str | Path,
        left_fighter_name: str = "",
    ) -> Path:
        output_path = Path(output_path)

        container = av.open(str(output_path), mode="w")
        stream = container.add_stream("libx264", rate=FPS)
        stream.width = W
        stream.height = H
        stream.pix_fmt = "yuv420p"
        stream.options = {"preset": "fast", "crf": "28", "tune": "animation"}

        for frame in self._timeline_frames(timeline):
            video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
            for packet in stream.encode(video_frame):
                container.mux(packet)

        for packet in stream.encode():
            container.mux(packet)

        container.close()
        logger.info(f"Battle video saved: {output_path}")
        return output_path

    # ======================================================
    # Async обёртка для aiogram
    # ======================================================

    async def generate_timeline_async(
        self,
        timeline: List[TimelineEvent],
        output_path: str | Path,
        left_fighter_name: str = "",
    ) -> Path:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                lambda: self.generate_timeline(
                    timeline, output_path, left_fighter_name
                ),
            )

    # ======================================================
    # Timeline → frames
    # ======================================================

    def _timeline_frames(self, timeline: List[TimelineEvent]) -> Iterator[np.ndarray]:
        for item in timeline:
            if item.type == "intro":
                yield from self._frames_intro(item)
            elif item.type == "pause":
                yield from self._frames_pause(item)
            elif item.type == "outro":
                yield from self._frames_outro(item)
            else:
                yield from self._frames_battle_event(item)

    # ======================================================
    # INTRO
    # ======================================================

    def _frames_intro(self, item):
        duration = item.duration or 2.5
        total = int(duration * FPS)
        left = item.data.left
        right = item.data.right

        font_name = ImageFont.truetype(FONT_CYR, int(H * 0.1))
        font_vs = ImageFont.truetype(FONT_MONO, int(H * 0.13))

        for i in range(total):
            progress = i / total
            ease = 1 - (1 - progress) ** 3

            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            center_y = H // 2
            lx = int(-W * 0.4 + (W // 4 + W * 0.4) * ease)
            rx = int(W + W * 0.4 - (W // 4 + W * 0.4) * ease)

            draw.text(
                (lx, center_y), left.name, font=font_name, fill=left.color, anchor="mm"
            )
            draw.text(
                (rx, center_y),
                right.name,
                font=font_name,
                fill=right.color,
                anchor="mm",
            )

            if progress > 0.7:
                alpha = (progress - 0.7) / 0.3
                vs_color = (int(220 * alpha),) * 3
                draw.text(
                    (W // 2, center_y), "VS", font=font_vs, fill=vs_color, anchor="mm"
                )

            yield np.array(img, dtype=np.uint8)

    # ======================================================
    # PAUSE
    # ======================================================

    def _frames_pause(self, item: TimelineEvent):
        duration = item.duration or 0.8
        total = int(duration * FPS)
        data = item.data

        left_path = get_animation_path(
            "idle", data.left.name, data.left.kagune_type, role="attacker"
        )
        right_path = get_animation_path(
            "idle", data.right.name, data.right.kagune_type, role="defender"
        )

        left_png = None if left_path else get_sprite(data.left, flip=False)
        right_png = None if right_path else get_sprite(data.right, flip=True)

        for i in range(total):
            progress = i / total

            if left_path:
                l_spr = get_clip_frame(left_path, progress, flip=False)
                ldx = ldy = la = 0
            else:
                l_spr, ldx, ldy, la = animate_idle(left_png, progress)

            if right_path:
                r_spr = get_clip_frame(right_path, progress, flip=True)
                rdx = rdy = ra = 0
            else:
                r_spr, rdx, rdy, ra = animate_idle(right_png, progress)

            frame = make_base_frame(
                left_hp=data.left_hp_before,
                right_hp=data.right_hp_before,
                left_max_hp=data.left.max_hp,
                right_max_hp=data.right.max_hp,
                left_name=data.left.name,
                right_name=data.right.name,
                left_color=data.left.color,
                right_color=data.right.color,
                left_sprite=l_spr,
                right_sprite=r_spr,
                left_sprite_offset=(ldx, ldy),
                right_sprite_offset=(rdx, rdy),
                left_sprite_angle=la,
                right_sprite_angle=ra,
                attacker_left=None,
            )
            yield frame

    # ======================================================
    # BATTLE EVENT
    # ======================================================

    def _frames_battle_event(self, item):
        event = item.data.battle_event
        left = item.data.left
        right = item.data.right
        attacker_left = item.data.attacker_left or False

        duration_map = {
            "hit": 1.0,
            "miss": 0.8,
            "block": 1.0,
            "crit": 2.0,
            "regen": 2.0,
        }
        total = int(duration_map[event.type] * FPS)

        attacker = left if attacker_left else right
        defender = right if attacker_left else left

        attacker_path = get_animation_path(
            event.type, attacker.name, attacker.kagune_type, role="attacker"
        )
        defender_path = get_animation_path(
            event.type, defender.name, defender.kagune_type, role="defender"
        )

        for i in range(total):
            progress = i / total

            left_hp = int(
                item.data.left_hp_before
                + (item.data.left_hp_after - item.data.left_hp_before) * progress
            )
            right_hp = int(
                item.data.right_hp_before
                + (item.data.right_hp_after - item.data.right_hp_before) * progress
            )

            if attacker_left:
                left_sprite = get_clip_frame(attacker_path, progress, flip=False)
                right_sprite = get_clip_frame(defender_path, progress, flip=True)
            else:
                right_sprite = get_clip_frame(attacker_path, progress, flip=True)
                left_sprite = get_clip_frame(defender_path, progress, flip=False)

            base = make_base_frame(
                left_hp=left_hp,
                right_hp=right_hp,
                left_max_hp=left.max_hp,
                right_max_hp=right.max_hp,
                left_name=left.name,
                right_name=right.name,
                left_color=left.color,
                right_color=right.color,
                left_sprite=left_sprite,
                right_sprite=right_sprite,
                attacker_left=attacker_left,
            )

            img = Image.fromarray(base)
            draw = ImageDraw.Draw(img)

            draw_event_label(draw, event.type, progress)
            draw_damage_number(
                draw,
                event.damage if event.type != "regen" else event.heal,
                event.type,
                progress,
                W // 2,
                DMG_Y,
            )
            draw_action_overlay(
                draw,
                event.type,
                event.attacker.name,
                event.defender.name,
                event.attacker.color,
                event.defender.color,
                attacker_left,
                progress,
            )

            yield np.array(img, dtype=np.uint8)

    # ======================================================
    # OUTRO
    # ======================================================

    def _frames_outro(self, item):
        duration = item.duration or 3.0
        total = int(duration * FPS)
        winner = item.data.winner
        is_draw = item.data.is_draw

        font_big = ImageFont.truetype(FONT_CYR, int(H * 0.117))
        font_small = ImageFont.truetype(FONT_CYR, int(H * 0.078))

        for i in range(total):
            t = i / FPS
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            center_y = H // 2

            if is_draw:
                draw.text(
                    (W // 2, center_y),
                    "НИЧЬЯ",
                    font=font_big,
                    fill=(180, 180, 180),
                    anchor="mm",
                )
            else:
                pulse = 0.7 + 0.3 * abs(np.sin(t * np.pi * 2))
                color = tuple(int(c * pulse) for c in winner.color)
                draw.text(
                    (W // 2, center_y - int(H * 0.11)),
                    "ПОБЕДИТЕЛЬ",
                    font=font_small,
                    fill=(200, 200, 200),
                    anchor="mm",
                )
                draw.text(
                    (W // 2, center_y + int(H * 0.03)),
                    winner.name,
                    font=font_big,
                    fill=color,
                    anchor="mm",
                )

            yield np.array(img, dtype=np.uint8)
