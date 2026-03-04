# src/bot/services/battle/benchmark.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

import statistics
import time

from src.bot.services.battle.generator import BattleVideoGenerator
from src.bot.services.battle.mechanics import BattleMechanics
from src.bot.services.battle.models import BattleFighter
from src.bot.services.battle.timeline import BattleTimelineBuilder
from src.bot.types import KaguneType

OUTPUT_DIR = Path("src/assets/videos/battle/benchmark")
N = 10


def make_fighter(name: str, kagune: KaguneType) -> BattleFighter:
    return BattleFighter(
        name=name,
        hp=1000,
        max_hp=1000,
        kagune_type=kagune,
        strength=50,
        dexterity=40,
        speed=35,
        kagune_strength=60,
        regeneration=20,
    )


def run():
    mechanics = BattleMechanics()
    builder = BattleTimelineBuilder()
    generator = BattleVideoGenerator(output_dir=OUTPUT_DIR)

    times = []

    for i in range(1, N + 1):
        left = make_fighter("Канеки", KaguneType.RINKAKU)
        right = make_fighter("Хайсе", KaguneType.RINKAKU)

        result = mechanics.simulate(left, right)
        timeline = builder.build(left, right, result)

        output_path = OUTPUT_DIR / f"bench_{i:02d}.mp4"

        print(f"[{i}/{N}] Генерация {output_path.name}... ", end="", flush=True)

        start = time.perf_counter()
        generator.generate_timeline(timeline, output_path, left_fighter_name=left.name)
        elapsed = time.perf_counter() - start

        times.append(elapsed)
        print(
            f"{elapsed:.2f}s  |  раундов: {result.rounds}  |  победитель: {result.winner.name if result.winner else 'ничья'}"
        )

    print("\n─── Статистика ───────────────────────────")
    print(f"  Мин:      {min(times):.2f}s")
    print(f"  Макс:     {max(times):.2f}s")
    print(f"  Среднее:  {statistics.mean(times):.2f}s")
    print(f"  Медиана:  {statistics.median(times):.2f}s")
    print(f"  Σ всего:  {sum(times):.2f}s")
    print("──────────────────────────────────────────")


if __name__ == "__main__":
    run()
