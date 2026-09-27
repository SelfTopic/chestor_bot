# Сгенерировано из src/bot/dialogs/*.yaml: python -m src.bot.dialogs.generate
# Руками не править: тест сверяет файл с YAML.
from .line import Line


class _CoffeeDialogs:
    def cooldown(self, *, hours: object, minutes: object, seconds: object) -> Line:
        return Line(
            "coffee.cooldown",
            {
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
            },
        )

    def done(self, *, count: object, money: object) -> Line:
        return Line("coffee.done", {"count": count, "money": money})

    def snap_limit(self) -> Line:
        return Line("coffee.snap_limit", {})


class _CombatPowerDialogs:
    def full(
        self,
        *,
        danger_rank: object,
        effective_dexterity: object,
        effective_health: object,
        effective_kagune: object,
        effective_power: object,
        effective_regeneration: object,
        effective_speed: object,
        effective_strength: object,
        name: object,
        vacuum_dexterity: object,
        vacuum_health: object,
        vacuum_kagune: object,
        vacuum_power: object,
        vacuum_regeneration: object,
        vacuum_speed: object,
        vacuum_strength: object,
    ) -> Line:
        return Line(
            "combat_power.full",
            {
                "danger_rank": danger_rank,
                "effective_dexterity": effective_dexterity,
                "effective_health": effective_health,
                "effective_kagune": effective_kagune,
                "effective_power": effective_power,
                "effective_regeneration": effective_regeneration,
                "effective_speed": effective_speed,
                "effective_strength": effective_strength,
                "name": name,
                "vacuum_dexterity": vacuum_dexterity,
                "vacuum_health": vacuum_health,
                "vacuum_kagune": vacuum_kagune,
                "vacuum_power": vacuum_power,
                "vacuum_regeneration": vacuum_regeneration,
                "vacuum_speed": vacuum_speed,
                "vacuum_strength": vacuum_strength,
            },
        )

    def short(self, *, effective_power: object, vacuum_power: object) -> Line:
        return Line(
            "combat_power.short",
            {
                "effective_power": effective_power,
                "vacuum_power": vacuum_power,
            },
        )


class _EatHumanDialogs:
    def cooldown(self, *, hours: object, minutes: object, seconds: object) -> Line:
        return Line(
            "eat_human.cooldown",
            {
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
            },
        )

    def done(self, *, count: object, hunger: object, restored: object) -> Line:
        return Line(
            "eat_human.done",
            {
                "count": count,
                "hunger": hunger,
                "restored": restored,
            },
        )


class _ErrorsDialogs:
    def not_enough_money(self, *, money: object) -> Line:
        return Line("errors.not_enough_money", {"money": money})

    def unexpected(self, *, error: object) -> Line:
        return Line("errors.unexpected", {"error": error})


class _FightDialogs:
    def not_ready(self, *, health: object, threshold: object) -> Line:
        return Line("fight.not_ready", {"health": health, "threshold": threshold})

    def summary(
        self,
        *,
        hp_line_a: object,
        hp_line_b: object,
        loser_line: object,
        rank_line_a: object,
        rank_line_b: object,
        rounds: object,
        winner_line: object,
    ) -> Line:
        return Line(
            "fight.summary",
            {
                "hp_line_a": hp_line_a,
                "hp_line_b": hp_line_b,
                "loser_line": loser_line,
                "rank_line_a": rank_line_a,
                "rank_line_b": rank_line_b,
                "rounds": rounds,
                "winner_line": winner_line,
            },
        )


class _GhoulDialogs:
    def dead(self) -> Line:
        return Line("ghoul.dead", {})

    def dead_profile(self, *, name: object) -> Line:
        return Line("ghoul.dead_profile", {"name": name})

    def new(self, *, kagune_type: object, name: object) -> Line:
        return Line("ghoul.new", {"kagune_type": kagune_type, "name": name})

    def profile(
        self,
        *,
        coffee_count: object,
        danger_rank: object,
        dexterity: object,
        eat_ghouls: object,
        eat_humans: object,
        health: object,
        is_kakuja: object,
        kagune_type: object,
        level: object,
        losses: object,
        max_health: object,
        mob_battles: object,
        mob_losses: object,
        mob_wins: object,
        name: object,
        power: object,
        rc_count: object,
        regeneration: object,
        snap_count: object,
        speed: object,
        strength: object,
        strength_kagune: object,
        total_battles: object,
        wins: object,
    ) -> Line:
        return Line(
            "ghoul.profile",
            {
                "coffee_count": coffee_count,
                "danger_rank": danger_rank,
                "dexterity": dexterity,
                "eat_ghouls": eat_ghouls,
                "eat_humans": eat_humans,
                "health": health,
                "is_kakuja": is_kakuja,
                "kagune_type": kagune_type,
                "level": level,
                "losses": losses,
                "max_health": max_health,
                "mob_battles": mob_battles,
                "mob_losses": mob_losses,
                "mob_wins": mob_wins,
                "name": name,
                "power": power,
                "rc_count": rc_count,
                "regeneration": regeneration,
                "snap_count": snap_count,
                "speed": speed,
                "strength": strength,
                "strength_kagune": strength_kagune,
                "total_battles": total_battles,
                "wins": wins,
            },
        )

    def reborn(self, *, kagune_type: object) -> Line:
        return Line("ghoul.reborn", {"kagune_type": kagune_type})


class _KaguneUpgradeDialogs:
    def cooldown(self, *, minutes: object, seconds: object) -> Line:
        return Line("kagune.upgrade.cooldown", {"minutes": minutes, "seconds": seconds})

    def done(self, *, kagune_strength: object, money: object) -> Line:
        return Line(
            "kagune.upgrade.done",
            {
                "kagune_strength": kagune_strength,
                "money": money,
            },
        )


class _KaguneDialogs:
    upgrade = _KaguneUpgradeDialogs()

    def info(self) -> Line:
        return Line("kagune.info", {})


class _LotteryDialogs:
    def lose(
        self,
        *,
        balance: object,
        bet: object,
        chosen_color: object,
        winning_color: object,
    ) -> Line:
        return Line(
            "lottery.lose",
            {
                "balance": balance,
                "bet": bet,
                "chosen_color": chosen_color,
                "winning_color": winning_color,
            },
        )

    def win(
        self,
        *,
        balance: object,
        bet: object,
        chosen_color: object,
        earned: object,
        multiplier: object,
        winning_color: object,
    ) -> Line:
        return Line(
            "lottery.win",
            {
                "balance": balance,
                "bet": bet,
                "chosen_color": chosen_color,
                "earned": earned,
                "multiplier": multiplier,
                "winning_color": winning_color,
            },
        )


class _NotifyDialogs:
    def death(
        self,
        *,
        cause: object,
        level: object,
        lifetime_rc_earned: object,
    ) -> Line:
        return Line(
            "notify.death",
            {
                "cause": cause,
                "level": level,
                "lifetime_rc_earned": lifetime_rc_earned,
            },
        )

    def health_full(self) -> Line:
        return Line("notify.health_full", {})

    def hunger(self, *, threshold: object) -> Line:
        return Line("notify.hunger", {"threshold": threshold})

    def level_up(
        self,
        *,
        cheston: object,
        level: object,
        rc: object,
        stat_changes: object,
    ) -> Line:
        return Line(
            "notify.level_up",
            {
                "cheston": cheston,
                "level": level,
                "rc": rc,
                "stat_changes": stat_changes,
            },
        )


class _SnapDialogs:
    def cooldown(self, *, minutes: object, seconds: object) -> Line:
        return Line("snap.cooldown", {"minutes": minutes, "seconds": seconds})

    def done(self, *, count: object, money: object) -> Line:
        return Line("snap.done", {"count": count, "money": money})


class _StatusDialogs:
    def hunger(
        self,
        *,
        effective_dexterity: object,
        effective_health: object,
        effective_kagune_strength: object,
        effective_regeneration: object,
        effective_speed: object,
        effective_strength: object,
        falling_multiplier: object,
        hunger: object,
        rising_multiplier: object,
        tier: object,
        time_left: object,
    ) -> Line:
        return Line(
            "status.hunger",
            {
                "effective_dexterity": effective_dexterity,
                "effective_health": effective_health,
                "effective_kagune_strength": effective_kagune_strength,
                "effective_regeneration": effective_regeneration,
                "effective_speed": effective_speed,
                "effective_strength": effective_strength,
                "falling_multiplier": falling_multiplier,
                "hunger": hunger,
                "rising_multiplier": rising_multiplier,
                "tier": tier,
                "time_left": time_left,
            },
        )

    def regen(
        self,
        *,
        health: object,
        hp_per_hour: object,
        max_health: object,
        time_left: object,
    ) -> Line:
        return Line(
            "status.regen",
            {
                "health": health,
                "hp_per_hour": hp_per_hour,
                "max_health": max_health,
                "time_left": time_left,
            },
        )


class _Dialogs:
    coffee = _CoffeeDialogs()
    combat_power = _CombatPowerDialogs()
    eat_human = _EatHumanDialogs()
    errors = _ErrorsDialogs()
    fight = _FightDialogs()
    ghoul = _GhoulDialogs()
    kagune = _KaguneDialogs()
    lottery = _LotteryDialogs()
    notify = _NotifyDialogs()
    snap = _SnapDialogs()
    status = _StatusDialogs()

    def balance(self, *, balance: object, name: object) -> Line:
        return Line("balance", {"balance": balance, "name": name})

    def bot(self) -> Line:
        return Line("bot", {})

    def help(self, *, commands_link: object, lore_link: object) -> Line:
        return Line("help", {"commands_link": commands_link, "lore_link": lore_link})

    def profile(self, *, balance: object, name: object, race: object) -> Line:
        return Line("profile", {"balance": balance, "name": name, "race": race})

    def start(self, *, name: object) -> Line:
        return Line("start", {"name": name})


Dialogs = _Dialogs()

PLACEHOLDERS: dict[str, frozenset[str]] = {
    "balance": frozenset({"balance", "name"}),
    "bot": frozenset(),
    "coffee.cooldown": frozenset({"hours", "minutes", "seconds"}),
    "coffee.done": frozenset({"count", "money"}),
    "coffee.snap_limit": frozenset(),
    "combat_power.full": frozenset(
        {
            "danger_rank",
            "effective_dexterity",
            "effective_health",
            "effective_kagune",
            "effective_power",
            "effective_regeneration",
            "effective_speed",
            "effective_strength",
            "name",
            "vacuum_dexterity",
            "vacuum_health",
            "vacuum_kagune",
            "vacuum_power",
            "vacuum_regeneration",
            "vacuum_speed",
            "vacuum_strength",
        }
    ),
    "combat_power.short": frozenset({"effective_power", "vacuum_power"}),
    "eat_human.cooldown": frozenset({"hours", "minutes", "seconds"}),
    "eat_human.done": frozenset({"count", "hunger", "restored"}),
    "errors.not_enough_money": frozenset({"money"}),
    "errors.unexpected": frozenset({"error"}),
    "fight.not_ready": frozenset({"health", "threshold"}),
    "fight.summary": frozenset(
        {
            "hp_line_a",
            "hp_line_b",
            "loser_line",
            "rank_line_a",
            "rank_line_b",
            "rounds",
            "winner_line",
        }
    ),
    "ghoul.dead": frozenset(),
    "ghoul.dead_profile": frozenset({"name"}),
    "ghoul.new": frozenset({"kagune_type", "name"}),
    "ghoul.profile": frozenset(
        {
            "coffee_count",
            "danger_rank",
            "dexterity",
            "eat_ghouls",
            "eat_humans",
            "health",
            "is_kakuja",
            "kagune_type",
            "level",
            "losses",
            "max_health",
            "mob_battles",
            "mob_losses",
            "mob_wins",
            "name",
            "power",
            "rc_count",
            "regeneration",
            "snap_count",
            "speed",
            "strength",
            "strength_kagune",
            "total_battles",
            "wins",
        }
    ),
    "ghoul.reborn": frozenset({"kagune_type"}),
    "help": frozenset({"commands_link", "lore_link"}),
    "kagune.info": frozenset(),
    "kagune.upgrade.cooldown": frozenset({"minutes", "seconds"}),
    "kagune.upgrade.done": frozenset({"kagune_strength", "money"}),
    "lottery.lose": frozenset({"balance", "bet", "chosen_color", "winning_color"}),
    "lottery.win": frozenset(
        {
            "balance",
            "bet",
            "chosen_color",
            "earned",
            "multiplier",
            "winning_color",
        }
    ),
    "notify.death": frozenset({"cause", "level", "lifetime_rc_earned"}),
    "notify.health_full": frozenset(),
    "notify.hunger": frozenset({"threshold"}),
    "notify.level_up": frozenset({"cheston", "level", "rc", "stat_changes"}),
    "profile": frozenset({"balance", "name", "race"}),
    "snap.cooldown": frozenset({"minutes", "seconds"}),
    "snap.done": frozenset({"count", "money"}),
    "start": frozenset({"name"}),
    "status.hunger": frozenset(
        {
            "effective_dexterity",
            "effective_health",
            "effective_kagune_strength",
            "effective_regeneration",
            "effective_speed",
            "effective_strength",
            "falling_multiplier",
            "hunger",
            "rising_multiplier",
            "tier",
            "time_left",
        }
    ),
    "status.regen": frozenset({"health", "hp_per_hour", "max_health", "time_left"}),
}
