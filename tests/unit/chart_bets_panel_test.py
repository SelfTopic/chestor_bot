import io

from PIL import Image

from src.bot.services.chart_game import PanelRow, bets_panel
from src.bot.services.chart_game.bets_panel import _clean


def height(png: bytes) -> int:
    return Image.open(io.BytesIO(png)).height


def test_panel_grows_with_players_and_draws_any_name():
    one = bets_panel("T", "B", [PanelRow("Вася", "1 000", None, None)])
    many = bets_panel(
        "T",
        "B",
        [
            PanelRow("🍆🍆", "100", "x3.00", 300, "eggplant"),
            PanelRow("山田太郎", "100", None, None),
            PanelRow("Очень длинный ник " * 10, "100 000", "x50.00", 5000),
        ],
    )

    assert height(many) > height(one)


def test_decorative_letters_become_plain_and_unknown_symbols_are_dropped():
    assert _clean("𝕮𝖍𝖊𝕾𝖙𝖔𝖗 𝕺𝖋𝖋𝖎𝖈𝖎𝖆𝖑") == "CheStor Official"
    assert _clean("Вася 🔥") == "Вася"
    assert _clean("🔥🔥") == ""
