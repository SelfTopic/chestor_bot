import numpy as np
import pytest
from PIL import Image

from src.bot.services.roulette.positions import (
    CENTER,
    POSITIONS,
    VISIBLE,
    color_of,
    positions_of,
    spin,
)
from src.bot.services.roulette.ribbon import RibbonPainter, motion_blur
from src.bot.services.roulette.spin_video import SpinFrames, rest_frame
from src.bot.types.dep import DepColor


@pytest.fixture(scope="module")
def painter() -> RibbonPainter:
    return RibbonPainter()


def test_every_color_has_two_rest_positions_with_different_neighbours():
    for color in DepColor:
        found = positions_of(color)
        assert len(found) == 2
        first, second = (POSITIONS[index] for index in found)
        assert first != second
    assert all(len(cards) == VISIBLE for cards in POSITIONS)


def test_every_spin_runs_from_one_rest_position_to_another():
    for start in range(len(POSITIONS)):
        for end in range(len(POSITIONS)):
            path = spin(start, end)
            assert path.cards[:VISIBLE] == POSITIONS[start]
            assert path.cards[-VISIBLE:] == POSITIONS[end]
            assert path.cards[path.start_card] is color_of(start)
            assert path.cards[path.end_card] is color_of(end)
            # Лента останавливается на выпавшей плашке, а не на соседней.
            assert 0 < abs(path.miss) < 0.5
            assert path == spin(start, end)


@pytest.mark.parametrize(("start", "end"), [(0, 6), (6, 6), (9, 2)])
def test_spin_starts_and_ends_on_the_rest_pictures(painter, start, end):
    frames = SpinFrames(spin(start, end), painter=painter)
    assert np.array_equal(np.asarray(frames.render(0)), np.asarray(rest_frame(start, painter)))
    last = frames.render(frames.count - 1)
    assert np.array_equal(np.asarray(last), np.asarray(rest_frame(end, painter)))


def test_rest_picture_lights_the_card_under_the_pointer(painter):
    still = np.asarray(rest_frame(4, painter)).astype(int)
    unlit = np.asarray(painter.frame(POSITIONS[4], CENTER * 168)).astype(int)
    middle, side = still.shape[1] // 2, still.shape[1] // 2 + 168
    assert abs(still[200, middle] - unlit[200, middle]).sum() > 0
    # Соседние плашки рядом с горящей тускнеют.
    assert still[200, side].sum() < unlit[200, side].sum()


def test_motion_blur_keeps_flat_colour_and_smears_edges():
    band = Image.new("RGBA", (40, 4))
    band.paste((255, 0, 0, 255), (0, 0, 20, 4))
    blurred = np.asarray(motion_blur(band.convert("RGBa"), 8).convert("RGBA")).astype(int)
    assert tuple(blurred[1, 5]) == (255, 0, 0, 255)
    assert tuple(blurred[1, 35]) == (0, 0, 0, 0)
    assert 0 < blurred[1, 20, 3] < 255
    assert motion_blur(band, 1) is band
