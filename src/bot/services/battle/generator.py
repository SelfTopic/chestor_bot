import logging
from pathlib import Path
from typing import List

import numpy as np
from moviepy import VideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

from src.bot.services.battle.effects import (
    _add_arrays,
    render_block,
    render_crit,
    render_hit,
    render_miss,
    render_regen,
)
from src.bot.services.battle.models import TimelineEvent
from src.bot.services.battle.renderer import (
    BG_COLOR,
    FONT_CYR,
    FONT_MONO,
    H,
    W,
    draw_damage_number,
    draw_event_label,
    make_base_frame,
)

logger = logging.getLogger(__name__)
FPS = 30


# ==========================================================
# Battle Video Generator
# ==========================================================


class BattleVideoGenerator:
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------
    # PUBLIC ENTRY
    # ------------------------------------------------------

    def generate_timeline(
        self,
        timeline: List[TimelineEvent],
        output_path: str | Path,
        left_fighter_name: str,
    ) -> Path:
        clips = []

        for item in timeline:
            if item.type == "intro":
                clips.append(self._render_intro(item))

            elif item.type == "pause":
                clips.append(self._render_pause(item))

            elif item.type == "turn":
                clips.append(self._render_turn(item, left_fighter_name))

            elif item.type == "outro":
                clips.append(self._render_outro(item))

            else:
                clips.append(self._render_battle_event(item))

        final = concatenate_videoclips(clips)
        output_path = Path(output_path)

        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio=False,
            logger=None,
            ffmpeg_params=["-crf", "28", "-preset", "fast"],
        )

        for clip in clips:
            clip.close()
        final.close()

        logger.info(f"Final battle video saved: {output_path}")
        return output_path

    # ======================================================
    # INTRO
    # ======================================================

    def _render_intro(self, item: TimelineEvent) -> VideoClip:
        duration = item.duration
        if not duration:
            raise ValueError("Duration is required for intro event type")
        left = item.data.left
        right = item.data.right

        def make_frame(t: float):
            progress = min(t / (duration * 0.5), 1.0)
            ease = 1 - (1 - progress) ** 3

            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            font_name = ImageFont.truetype(FONT_CYR, 36)
            font_vs = ImageFont.truetype(FONT_MONO, 48)

            center_y = H // 2

            # Left
            a_target = W // 4
            a_start = -200
            a_x = int(a_start + (a_target - a_start) * ease)

            draw.text(
                (a_x, center_y),
                left.name,
                font=font_name,
                fill=left.color,
                anchor="mm",
            )

            # Right
            b_target = W * 3 // 4
            b_start = W + 200
            b_x = int(b_start + (b_target - b_start) * ease)

            draw.text(
                (b_x, center_y),
                right.name,
                font=font_name,
                fill=right.color,
                anchor="mm",
            )

            # VS
            if progress > 0.7:
                alpha = (progress - 0.7) / 0.3
                vs_color = (int(220 * alpha),) * 3
                draw.text(
                    (W // 2, center_y),
                    "VS",
                    font=font_vs,
                    fill=vs_color,
                    anchor="mm",
                )

            return np.array(img)

        return VideoClip(make_frame, duration=duration)

    # ======================================================
    # PAUSE
    # ======================================================

    def _render_pause(self, item: TimelineEvent) -> VideoClip:
        duration = item.duration
        data = item.data

        def make_frame(t: float):
            return make_base_frame(
                attacker_hp=data.left.hp,
                defender_hp=data.right.hp,
                attacker_max_hp=data.left.max_hp,
                defender_max_hp=data.right.max_hp,
                attacker_name=data.left.name,
                defender_name=data.right.name,
                attacker_color=data.left.color,
                defender_color=data.right.color,
            )

        return VideoClip(make_frame, duration=duration)

    # ======================================================
    # TURN ARROW
    # ======================================================

    def _render_turn(self, item: TimelineEvent, left_name: str) -> VideoClip:
        duration = item.duration
        if not duration:
            raise ValueError("Duration is required for turn event type")
        attacker = item.data.left if item.data.attacker_left else item.data.right

        left = item.data.left
        right = item.data.right
        left_hp = item.data.left.hp
        right_hp = item.data.right.hp

        def make_frame(t: float):
            base = make_base_frame(
                attacker_hp=left_hp,
                defender_hp=right_hp,
                attacker_max_hp=left.max_hp,
                defender_max_hp=right.max_hp,
                attacker_name=left.name,
                defender_name=right.name,
                attacker_color=left.color,
                defender_color=right.color,
            )

            progress = t / duration
            pulse = abs(np.sin(progress * np.pi * 4))
            intensity = int(150 + pulse * 100)

            overlay = np.zeros_like(base)
            img = Image.fromarray(overlay)
            draw = ImageDraw.Draw(img)

            y = H // 2
            size = 40

            attacker_left = attacker.name == left_name

            if attacker_left:
                points = [
                    (W // 4 + size, y),
                    (W // 4, y - size),
                    (W // 4, y + size),
                ]
            else:
                x = W * 3 // 4
                points = [
                    (x - size, y),
                    (x, y - size),
                    (x, y + size),
                ]

            draw.polygon(points, fill=(255, 255, 255, intensity))

            return _add_arrays(base, np.array(img))

        return VideoClip(make_frame, duration=duration)

    # ======================================================
    # OUTRO
    # ======================================================

    def _render_outro(self, item: TimelineEvent) -> VideoClip:
        duration = item.duration
        winner = item.data.winner

        if not winner or not duration:
            raise ValueError("Winner and duration are required for outro event type")

        is_draw = item.data.is_draw

        def make_frame(t: float):
            img = Image.new("RGB", (W, H), BG_COLOR)
            draw = ImageDraw.Draw(img)

            font_big = ImageFont.truetype(FONT_CYR, 42)
            font_small = ImageFont.truetype(FONT_CYR, 28)

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
                    (W // 2, center_y - 40),
                    "ПОБЕДИТЕЛЬ",
                    font=font_small,
                    fill=(200, 200, 200),
                    anchor="mm",
                )

                draw.text(
                    (W // 2, center_y + 10),
                    winner.name,
                    font=font_big,
                    fill=color,
                    anchor="mm",
                )

            return np.array(img)

        return VideoClip(make_frame, duration=duration)

    # ======================================================
    # BATTLE EVENT
    # ======================================================

    def _render_battle_event(self, item: TimelineEvent) -> VideoClip:
        event = item.battle_event
        if not event:
            raise ValueError("Battle event data is required for battle event type")
        left = item.data.left
        right = item.data.right

        left_hp = item.data.left.hp
        right_hp = item.data.right.hp

        attacker_left = item.data.attacker_left
        left_hp_before = item.data.left_hp_before
        right_hp_before = item.data.right_hp_before
        right_hp_after = item.data.right_hp_after
        left_hp_after = item.data.left_hp_after

        duration = {
            "hit": 1.5,
            "miss": 1.0,
            "block": 1.5,
            "crit": 2.5,
            "regen": 3.0,
        }[event.type]

        def make_frame(t: float):
            progress = min(max(t / duration, 0), 1)

            # плавная интерполяция
            left_hp = int(left_hp_before + (left_hp_after - left_hp_before) * progress)
            right_hp = int(
                right_hp_before + (right_hp_after - right_hp_before) * progress
            )
            # ВСЕГДА рисуем одних и тех же бойцов слева и справа
            base = make_base_frame(
                attacker_hp=left_hp,
                defender_hp=right_hp,
                attacker_max_hp=left.max_hp,
                defender_max_hp=right.max_hp,
                attacker_name=left.name,
                defender_name=right.name,
                attacker_color=left.color,
                defender_color=right.color,
            )

            cx = W // 4 if attacker_left else W * 3 // 4
            cy = H // 2

            if event.type == "hit":
                base = render_hit(base, t, duration, event.attacker.color, cx, cy)
            elif event.type == "miss":
                base = render_miss(base, t, duration, cx, cy)
            elif event.type == "block":
                base = render_block(base, t, duration, event.defender.color, cx, cy)
            elif event.type == "crit":
                base = render_crit(base, t, duration, event.attacker.color, cx, cy)
            elif event.type == "regen":
                base = render_regen(base, t, duration, cx, cy)

            img = Image.fromarray(base)
            draw = ImageDraw.Draw(img)

            draw_event_label(draw, event.type, t / duration)
            draw_damage_number(
                draw,
                event.damage,
                event.type,
                t / duration,
                cx,
                cy - 40,
            )

            return np.array(img)

        return VideoClip(make_frame, duration=duration)
