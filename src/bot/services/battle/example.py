import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from src.bot.services.battle.generator import (
    BattleVideoGenerator,
)
from src.bot.services.battle.mechanics import BattleMechanics
from src.bot.services.battle.models import BattleFighter
from src.bot.services.battle.timeline import BattleTimelineBuilder
from src.bot.types import KaguneType

# ==========================================================
# Создание бойцов
# ==========================================================

fighter_a = BattleFighter(
    name="Канеки",
    hp=100,
    max_hp=100,
    kagune_type=KaguneType.RINKAKU,
    strength=15,
    dexterity=12,
    speed=10,
    kagune_strength=8,
    regeneration=5,
)

fighter_b = BattleFighter(
    name="Ями",
    hp=120,
    max_hp=120,
    kagune_type=KaguneType.KOUKAKU,
    strength=10,
    dexterity=8,
    speed=8,
    kagune_strength=10,
    regeneration=3,
)


# ==========================================================
# Симуляция боя
# ==========================================================

print("Симуляция боя...")

mechanics = BattleMechanics()
result = mechanics.simulate(fighter_a, fighter_b)

print(f"Раундов: {result.rounds}")
print(f"Победитель: {result.winner.name}")
print(f"Ничья: {result.is_draw}")


# ==========================================================
# Построение таймлайна
# ==========================================================

print("Построение timeline...")

timeline_builder = BattleTimelineBuilder()
timeline = timeline_builder.build(fighter_a, fighter_b, result)

print(f"Событий в таймлайне: {len(timeline)}")


# ==========================================================
# Генерация видео
# ==========================================================

print("Генерация видео...")

output_dir = Path("src/assets/videos/battle/fight_timeline")
output_dir.mkdir(parents=True, exist_ok=True)

generator = BattleVideoGenerator(output_dir)

output_path = output_dir / "full_fight.mp4"

generator.generate_timeline(
    timeline=timeline,
    output_path=output_path,
    left_fighter_name=fighter_a.name,
)

print(f"\n✓ Готово: {output_path}")
