# Сгенерировано из src/bot/dialogs/*.yaml: python -m src.bot.dialogs.generate
# Руками не править: тест сверяет файл с YAML.
from .line import Line


class _AnimeDialogs:
    def bad_end(self) -> Line:
        return Line("anime.bad_end", {})

    def bad_format(self) -> Line:
        return Line("anime.bad_format", {})

    def bad_start(self) -> Line:
        return Line("anime.bad_start", {})

    def busy(self) -> Line:
        return Line("anime.busy", {})

    def cancelled(self) -> Line:
        return Line("anime.cancelled", {})

    def cut_caption(
        self,
        *,
        end: object,
        episode: object,
        season: object,
        start: object,
    ) -> Line:
        return Line(
            "anime.cut_caption",
            {
                "end": end,
                "episode": episode,
                "season": season,
                "start": start,
            },
        )

    def cutting(
        self,
        *,
        end: object,
        episode: object,
        season: object,
        start: object,
    ) -> Line:
        return Line(
            "anime.cutting",
            {
                "end": end,
                "episode": episode,
                "season": season,
                "start": start,
            },
        )

    def end_before_start(self) -> Line:
        return Line("anime.end_before_start", {})

    def episode_caption(self, *, episode: object, season: object) -> Line:
        return Line("anime.episode_caption", {"episode": episode, "season": season})

    def failed(self, *, error: object) -> Line:
        return Line("anime.failed", {"error": error})

    def gif(self, *, caption: object) -> Line:
        return Line("anime.gif", {"caption": caption})

    def not_found(self, *, episode: object, season: object) -> Line:
        return Line("anime.not_found", {"episode": episode, "season": season})

    def queue_full(self) -> Line:
        return Line("anime.queue_full", {})

    def timeout(self) -> Line:
        return Line("anime.timeout", {})

    def usage(self) -> Line:
        return Line("anime.usage", {})

    def video(self, *, caption: object) -> Line:
        return Line("anime.video", {"caption": caption})


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
    def chat_not_found(self) -> Line:
        return Line("errors.chat_not_found", {})

    def media_not_found(self) -> Line:
        return Line("errors.media_not_found", {})

    def not_enough_money(self, *, money: object) -> Line:
        return Line("errors.not_enough_money", {"money": money})

    def unexpected(self, *, error: object) -> Line:
        return Line("errors.unexpected", {"error": error})

    def user_not_found(self, *, query: object) -> Line:
        return Line("errors.user_not_found", {"query": query})

    def username_not_found(self, *, username: object) -> Line:
        return Line("errors.username_not_found", {"username": username})


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


class _FunCalculatorDialogs:
    def division_by_zero(self) -> Line:
        return Line("fun.calculator.division_by_zero", {})

    def too_big(self) -> Line:
        return Line("fun.calculator.too_big", {})


class _FunPickDialogs:
    def result(self, *, choice: object) -> Line:
        return Line("fun.pick.result", {"choice": choice})

    def too_few(self) -> Line:
        return Line("fun.pick.too_few", {})

    def too_long(self) -> Line:
        return Line("fun.pick.too_long", {})

    def too_many(self, *, max_items: object) -> Line:
        return Line("fun.pick.too_many", {"max_items": max_items})


class _FunDialogs:
    calculator = _FunCalculatorDialogs()
    pick = _FunPickDialogs()

    def nobody(self) -> Line:
        return Line("fun.nobody", {})

    def number(self, *, number: object) -> Line:
        return Line("fun.number", {"number": number})

    def random_participant(self, *, mention: object) -> Line:
        return Line("fun.random_participant", {"mention": mention})

    def who(self, *, mention: object, question: object) -> Line:
        return Line("fun.who", {"mention": mention, "question": question})


class _GhoulRichProfileDialogs:
    def kagune_types(self) -> Line:
        return Line("ghoul.rich_profile.kagune_types", {})

    def stats(self) -> Line:
        return Line("ghoul.rich_profile.stats", {})

    def title(self, *, danger_rank: object, name: object) -> Line:
        return Line(
            "ghoul.rich_profile.title",
            {
                "danger_rank": danger_rank,
                "name": name,
            },
        )


class _GhoulDialogs:
    rich_profile = _GhoulRichProfileDialogs()

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


class _KaguneGuideDialogs:
    def general(self) -> Line:
        return Line("kagune.guide.general", {})

    def general_title(self) -> Line:
        return Line("kagune.guide.general_title", {})

    def table_notes(self) -> Line:
        return Line("kagune.guide.table_notes", {})

    def table_title(self) -> Line:
        return Line("kagune.guide.table_title", {})


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
    guide = _KaguneGuideDialogs()
    upgrade = _KaguneUpgradeDialogs()

    def info(self) -> Line:
        return Line("kagune.info", {})


class _LotteryDialogs:
    def bet_out_of_range(self, *, max_bet: object, min_bet: object) -> Line:
        return Line(
            "lottery.bet_out_of_range",
            {
                "max_bet": max_bet,
                "min_bet": min_bet,
            },
        )

    def failed(self) -> Line:
        return Line("lottery.failed", {})

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

    def not_enough_money(self) -> Line:
        return Line("lottery.not_enough_money", {})

    def player_missing(self) -> Line:
        return Line("lottery.player_missing", {})

    def unknown_color(self, *, color: object, colors: object) -> Line:
        return Line("lottery.unknown_color", {"color": color, "colors": colors})

    def usage(self) -> Line:
        return Line("lottery.usage", {})

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


class _ProfileDialogs:
    def card(self, *, balance: object, name: object, race: object) -> Line:
        return Line("profile.card", {"balance": balance, "name": name, "race": race})

    def unknown_race(self) -> Line:
        return Line("profile.unknown_race", {})


class _RpDialogs:
    def created(self, *, action: object, command: object) -> Line:
        return Line("rp.created", {"action": action, "command": command})

    def delete_usage(self) -> Line:
        return Line("rp.delete_usage", {})

    def deleted(self, *, command: object) -> Line:
        return Line("rp.deleted", {"command": command})

    def empty(self) -> Line:
        return Line("rp.empty", {})

    def limit_reached(self, *, limit: object) -> Line:
        return Line("rp.limit_reached", {"limit": limit})

    def list(self, *, rows: object) -> Line:
        return Line("rp.list", {"rows": rows})

    def media_usage(self) -> Line:
        return Line("rp.media_usage", {})

    def not_found(self) -> Line:
        return Line("rp.not_found", {})

    def row(self, *, action: object, command: object, place: object) -> Line:
        return Line("rp.row", {"action": action, "command": command, "place": place})

    def set_usage(self) -> Line:
        return Line("rp.set_usage", {})


class _RulesDialogs:
    def missing(self) -> Line:
        return Line("rules.missing", {})


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


class _TopsBalanceDialogs:
    def bad_count(self) -> Line:
        return Line("tops.balance.bad_count", {})

    def row(self, *, balance: object, name: object, place: object) -> Line:
        return Line(
            "tops.balance.row",
            {
                "balance": balance,
                "name": name,
                "place": place,
            },
        )

    def text(self, *, count: object, rows: object) -> Line:
        return Line("tops.balance.text", {"count": count, "rows": rows})


class _TopsDialogs:
    balance = _TopsBalanceDialogs()


class _TransferButtonsDialogs:
    def confirm(self) -> Line:
        return Line("transfer.buttons.confirm", {})

    def confirm_decline(self) -> Line:
        return Line("transfer.buttons.confirm_decline", {})

    def decline(self) -> Line:
        return Line("transfer.buttons.decline", {})

    def surely_decline(self) -> Line:
        return Line("transfer.buttons.surely_decline", {})


class _TransferErrorsDialogs:
    def amount_out_of_range(self, *, max_amount: object, min_amount: object) -> Line:
        return Line(
            "transfer.errors.amount_out_of_range",
            {
                "max_amount": max_amount,
                "min_amount": min_amount,
            },
        )

    def failed(self) -> Line:
        return Line("transfer.errors.failed", {})

    def insufficient_balance(self) -> Line:
        return Line("transfer.errors.insufficient_balance", {})

    def receiver_limit(self) -> Line:
        return Line("transfer.errors.receiver_limit", {})

    def receiver_missing(self) -> Line:
        return Line("transfer.errors.receiver_missing", {})

    def receiver_vanished(self) -> Line:
        return Line("transfer.errors.receiver_vanished", {})

    def self_transfer(self) -> Line:
        return Line("transfer.errors.self_transfer", {})

    def sender_missing(self) -> Line:
        return Line("transfer.errors.sender_missing", {})

    def sender_too_new(self, *, days: object) -> Line:
        return Line("transfer.errors.sender_too_new", {"days": days})


class _TransferDialogs:
    buttons = _TransferButtonsDialogs()
    errors = _TransferErrorsDialogs()

    def ask(self, *, amount: object, confirm: object, receiver: object) -> Line:
        return Line(
            "transfer.ask",
            {
                "amount": amount,
                "confirm": confirm,
                "receiver": receiver,
            },
        )

    def ask_again(self, *, amount: object, confirm: object) -> Line:
        return Line("transfer.ask_again", {"amount": amount, "confirm": confirm})

    def cancelled(self) -> Line:
        return Line("transfer.cancelled", {})

    def done(self, *, amount: object) -> Line:
        return Line("transfer.done", {"amount": amount})

    def reply_usage(self) -> Line:
        return Line("transfer.reply_usage", {})

    def usage(self) -> Line:
        return Line("transfer.usage", {})


class _WordleErrorsDialogs:
    def not_russian(self) -> Line:
        return Line("wordle.errors.not_russian", {})

    def wrong_length(self, *, length: object) -> Line:
        return Line("wordle.errors.wrong_length", {"length": length})


class _WordleGuessDialogs:
    def lost(self, *, word: object) -> Line:
        return Line("wordle.guess.lost", {"word": word})

    def miss(
        self,
        *,
        board: object,
        left: object,
        max_attempts: object,
        used: object,
        word: object,
    ) -> Line:
        return Line(
            "wordle.guess.miss",
            {
                "board": board,
                "left": left,
                "max_attempts": max_attempts,
                "used": used,
                "word": word,
            },
        )

    def won(
        self,
        *,
        attempts: object,
        attempts_word: object,
        board: object,
        word: object,
    ) -> Line:
        return Line(
            "wordle.guess.won",
            {
                "attempts": attempts,
                "attempts_word": attempts_word,
                "board": board,
                "word": word,
            },
        )


class _WordleDialogs:
    errors = _WordleErrorsDialogs()
    guess = _WordleGuessDialogs()

    def lose(self, *, wiki: object, word: object) -> Line:
        return Line("wordle.lose", {"wiki": wiki, "word": word})

    def new_game(self) -> Line:
        return Line("wordle.new_game", {})

    def resume(self) -> Line:
        return Line("wordle.resume", {})

    def wiki_extract(self, *, extract: object) -> Line:
        return Line("wordle.wiki_extract", {"extract": extract})

    def win(
        self,
        *,
        attempts: object,
        attempts_word: object,
        award: object,
        wiki: object,
        word: object,
    ) -> Line:
        return Line(
            "wordle.win",
            {
                "attempts": attempts,
                "attempts_word": attempts_word,
                "award": award,
                "wiki": wiki,
                "word": word,
            },
        )


class _Dialogs:
    anime = _AnimeDialogs()
    coffee = _CoffeeDialogs()
    combat_power = _CombatPowerDialogs()
    eat_human = _EatHumanDialogs()
    errors = _ErrorsDialogs()
    fight = _FightDialogs()
    fun = _FunDialogs()
    ghoul = _GhoulDialogs()
    kagune = _KaguneDialogs()
    lottery = _LotteryDialogs()
    notify = _NotifyDialogs()
    profile = _ProfileDialogs()
    rp = _RpDialogs()
    rules = _RulesDialogs()
    snap = _SnapDialogs()
    status = _StatusDialogs()
    tops = _TopsDialogs()
    transfer = _TransferDialogs()
    wordle = _WordleDialogs()

    def balance(self, *, balance: object, name: object) -> Line:
        return Line("balance", {"balance": balance, "name": name})

    def bot(self) -> Line:
        return Line("bot", {})

    def help(self) -> Line:
        return Line("help", {})

    def start(self, *, name: object) -> Line:
        return Line("start", {"name": name})


Dialogs = _Dialogs()

PLACEHOLDERS: dict[str, frozenset[str]] = {
    "anime.bad_end": frozenset(),
    "anime.bad_format": frozenset(),
    "anime.bad_start": frozenset(),
    "anime.busy": frozenset(),
    "anime.cancelled": frozenset(),
    "anime.cut_caption": frozenset({"end", "episode", "season", "start"}),
    "anime.cutting": frozenset({"end", "episode", "season", "start"}),
    "anime.end_before_start": frozenset(),
    "anime.episode_caption": frozenset({"episode", "season"}),
    "anime.failed": frozenset({"error"}),
    "anime.gif": frozenset({"caption"}),
    "anime.not_found": frozenset({"episode", "season"}),
    "anime.queue_full": frozenset(),
    "anime.timeout": frozenset(),
    "anime.usage": frozenset(),
    "anime.video": frozenset({"caption"}),
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
    "errors.chat_not_found": frozenset(),
    "errors.media_not_found": frozenset(),
    "errors.not_enough_money": frozenset({"money"}),
    "errors.unexpected": frozenset({"error"}),
    "errors.user_not_found": frozenset({"query"}),
    "errors.username_not_found": frozenset({"username"}),
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
    "fun.calculator.division_by_zero": frozenset(),
    "fun.calculator.too_big": frozenset(),
    "fun.nobody": frozenset(),
    "fun.number": frozenset({"number"}),
    "fun.pick.result": frozenset({"choice"}),
    "fun.pick.too_few": frozenset(),
    "fun.pick.too_long": frozenset(),
    "fun.pick.too_many": frozenset({"max_items"}),
    "fun.random_participant": frozenset({"mention"}),
    "fun.who": frozenset({"mention", "question"}),
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
    "ghoul.rich_profile.kagune_types": frozenset(),
    "ghoul.rich_profile.stats": frozenset(),
    "ghoul.rich_profile.title": frozenset({"danger_rank", "name"}),
    "help": frozenset(),
    "kagune.guide.general": frozenset(),
    "kagune.guide.general_title": frozenset(),
    "kagune.guide.table_notes": frozenset(),
    "kagune.guide.table_title": frozenset(),
    "kagune.info": frozenset(),
    "kagune.upgrade.cooldown": frozenset({"minutes", "seconds"}),
    "kagune.upgrade.done": frozenset({"kagune_strength", "money"}),
    "lottery.bet_out_of_range": frozenset({"max_bet", "min_bet"}),
    "lottery.failed": frozenset(),
    "lottery.lose": frozenset({"balance", "bet", "chosen_color", "winning_color"}),
    "lottery.not_enough_money": frozenset(),
    "lottery.player_missing": frozenset(),
    "lottery.unknown_color": frozenset({"color", "colors"}),
    "lottery.usage": frozenset(),
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
    "profile.card": frozenset({"balance", "name", "race"}),
    "profile.unknown_race": frozenset(),
    "rp.created": frozenset({"action", "command"}),
    "rp.delete_usage": frozenset(),
    "rp.deleted": frozenset({"command"}),
    "rp.empty": frozenset(),
    "rp.limit_reached": frozenset({"limit"}),
    "rp.list": frozenset({"rows"}),
    "rp.media_usage": frozenset(),
    "rp.not_found": frozenset(),
    "rp.row": frozenset({"action", "command", "place"}),
    "rp.set_usage": frozenset(),
    "rules.missing": frozenset(),
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
    "tops.balance.bad_count": frozenset(),
    "tops.balance.row": frozenset({"balance", "name", "place"}),
    "tops.balance.text": frozenset({"count", "rows"}),
    "transfer.ask": frozenset({"amount", "confirm", "receiver"}),
    "transfer.ask_again": frozenset({"amount", "confirm"}),
    "transfer.buttons.confirm": frozenset(),
    "transfer.buttons.confirm_decline": frozenset(),
    "transfer.buttons.decline": frozenset(),
    "transfer.buttons.surely_decline": frozenset(),
    "transfer.cancelled": frozenset(),
    "transfer.done": frozenset({"amount"}),
    "transfer.errors.amount_out_of_range": frozenset({"max_amount", "min_amount"}),
    "transfer.errors.failed": frozenset(),
    "transfer.errors.insufficient_balance": frozenset(),
    "transfer.errors.receiver_limit": frozenset(),
    "transfer.errors.receiver_missing": frozenset(),
    "transfer.errors.receiver_vanished": frozenset(),
    "transfer.errors.self_transfer": frozenset(),
    "transfer.errors.sender_missing": frozenset(),
    "transfer.errors.sender_too_new": frozenset({"days"}),
    "transfer.reply_usage": frozenset(),
    "transfer.usage": frozenset(),
    "wordle.errors.not_russian": frozenset(),
    "wordle.errors.wrong_length": frozenset({"length"}),
    "wordle.guess.lost": frozenset({"word"}),
    "wordle.guess.miss": frozenset({"board", "left", "max_attempts", "used", "word"}),
    "wordle.guess.won": frozenset({"attempts", "attempts_word", "board", "word"}),
    "wordle.lose": frozenset({"wiki", "word"}),
    "wordle.new_game": frozenset(),
    "wordle.resume": frozenset(),
    "wordle.wiki_extract": frozenset({"extract"}),
    "wordle.win": frozenset({"attempts", "attempts_word", "award", "wiki", "word"}),
}
