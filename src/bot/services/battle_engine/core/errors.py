class InvalidBattleStatsError(ValueError):
    """2.4d в BATTLE_ENGINE.md - если у бойца обнаружены невозможные статы
    (например dexterity<=0), бой не считается вообще, а не падает делением
    на 0. Поднимается из конструктора Fighter - ошибка ловится максимально
    рано, до создания самого Battle."""


__all__ = ["InvalidBattleStatsError"]
