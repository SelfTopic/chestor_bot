class BattleError(Exception):
    """Common base class for "бой невозможен" errors - см.
    BattleService.validate_ghoul/validate_duel. Вызывать validate ПЕРЕД
    любой попыткой построить Fighter/Battle - не тратить время на сборку
    боя, который всё равно нельзя провести."""

    def __init__(self, message: str = "Бой невозможен") -> None:
        super().__init__(message)


class FighterIsDeadError(BattleError):
    def __init__(self, ghoul_id: int) -> None:
        self.ghoul_id = ghoul_id
        super().__init__(f"Гуль {ghoul_id} мёртв и не может драться")


class FighterNotCombatReadyError(BattleError):
    """HP ниже порога небоеспособности (BATTLE_CONFIG.min_health_to_fight) -
    не мёртв, но драться в таком состоянии нельзя."""

    def __init__(self, ghoul_id: int, health: int, threshold: int) -> None:
        self.ghoul_id = ghoul_id
        self.health = health
        self.threshold = threshold
        super().__init__(
            f"Гуль {ghoul_id} небоеспособен: {health} HP (нужно минимум {threshold})"
        )


class FighterHasPendingBattleError(BattleError):
    """У гуля уже есть неподтверждённый вызов на бой - не дать драться
    сразу с двумя (иначе статы одного боя перезатирались бы другим).
    Персистентности для отслеживания pending-вызовов пока нет (флоу
    согласия на дуэль ещё не построен, см. BATTLE_ENGINE.md 1.1/1.5) -
    проверка появится, когда появится хранилище."""

    def __init__(self, ghoul_id: int) -> None:
        self.ghoul_id = ghoul_id
        super().__init__(f"У гуля {ghoul_id} уже есть неподтверждённый вызов на бой")


__all__ = [
    "BattleError",
    "FighterIsDeadError",
    "FighterNotCombatReadyError",
    "FighterHasPendingBattleError",
]
