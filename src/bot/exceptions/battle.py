class BattleError(Exception):
    def __init__(self, message: str = "Бой невозможен") -> None:
        super().__init__(message)


class FighterIsDeadError(BattleError):
    def __init__(self, ghoul_id: int) -> None:
        self.ghoul_id = ghoul_id
        super().__init__(f"Гуль {ghoul_id} мёртв и не может драться")


class FighterNotCombatReadyError(BattleError):
    def __init__(self, ghoul_id: int, health: int, threshold: int) -> None:
        self.ghoul_id = ghoul_id
        self.health = health
        self.threshold = threshold
        super().__init__(
            f"Гуль {ghoul_id} небоеспособен: {health} HP (нужно минимум {threshold})"
        )


class FighterHasPendingBattleError(BattleError):
    def __init__(self, ghoul_id: int) -> None:
        self.ghoul_id = ghoul_id
        super().__init__(f"У гуля {ghoul_id} уже есть неподтверждённый вызов на бой")


__all__ = [
    "BattleError",
    "FighterIsDeadError",
    "FighterNotCombatReadyError",
    "FighterHasPendingBattleError",
]
