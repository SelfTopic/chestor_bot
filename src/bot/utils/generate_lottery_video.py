import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent))
from src.bot.services.lottery_video_genertor import LotteryGenerator

if __name__ == "__main__":
    generator = LotteryGenerator(
        output_dir=pathlib.Path(__file__).parent.parent.parent.parent
        / "src"
        / "assets"
        / "videos"
        / "lottery",
    )
    generator.generate_all()
