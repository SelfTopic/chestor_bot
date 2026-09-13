import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent))
from src.bot.services.lottery_video_genertor import LotteryGenerator

# Одна попытка ротации за запуск - цикл "раз в N минут" живёт СНАРУЖИ,
# в docker-compose (тот же приём, что уже используется для rclone_backup:
# `while true; do <команда>; sleep <N>; done` в entrypoint), а не здесь.
# Так проще прогнать вручную ("одна попытка и вышел") и не плодить свой
# планировщик внутри процесса, который и так не связан с ботом.
if __name__ == "__main__":
    generator = LotteryGenerator(
        output_dir=pathlib.Path(__file__).parent.parent.parent.parent
        / "src"
        / "assets"
        / "videos"
        / "lottery",
    )
    generator.rotate_all(replace_count=2)
