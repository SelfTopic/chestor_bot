class BattleError(Exception): ...


class FighterIsDeadError(BattleError):
    def __init__(self, ghoul_id: int) -> None:
        super().__init__(ghoul_id)
        self.ghoul_id = ghoul_id


class FighterNotCombatReadyError(BattleError):
    def __init__(self, ghoul_id: int, health: int, threshold: int) -> None:
        super().__init__(ghoul_id, health, threshold)
        self.ghoul_id = ghoul_id
        self.health = health
        self.threshold = threshold


class FighterHasPendingBattleError(BattleError):
    def __init__(self, ghoul_id: int) -> None:
        super().__init__(ghoul_id)
        self.ghoul_id = ghoul_id


__all__ = [
    "BattleError",
    "FighterIsDeadError",
    "FighterNotCombatReadyError",
    "FighterHasPendingBattleError",
]
