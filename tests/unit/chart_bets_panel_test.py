import io

from PIL import Image

from src.bot.services.chart_game import PanelRow, bets_panel


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
