# Сгенерировано из src/bot/dialogs/*.yaml: python -m src.bot.dialogs.generate
# Руками не править: тест сверяет файл с YAML.
from .line import Line


class _AdminBanDialogs:
    def already(self) -> Line:
        return Line("admin.ban.already", {})

    def done(self, *, id: object, name: object, reason: object, term: object) -> Line:
        return Line(
            "admin.ban.done",
            {
                "id": id,
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def usage(self) -> Line:
        return Line("admin.ban.usage", {})


class _AdminBroadcastDialogs:
    def all_usage(self) -> Line:
        return Line("admin.broadcast.all_usage", {})

    def blocked(self) -> Line:
        return Line("admin.broadcast.blocked", {})

    def chats_usage(self) -> Line:
        return Line("admin.broadcast.chats_usage", {})

    def finished(self, *, failed: object, success: object, total: object) -> Line:
        return Line(
            "admin.broadcast.finished",
            {
                "failed": failed,
                "success": success,
                "total": total,
            },
        )

    def private_usage(self) -> Line:
        return Line("admin.broadcast.private_usage", {})

    def sent(self) -> Line:
        return Line("admin.broadcast.sent", {})

    def started(self) -> Line:
        return Line("admin.broadcast.started", {})

    def user_usage(self) -> Line:
        return Line("admin.broadcast.user_usage", {})


class _AdminCooldownDialogs:
    def all_cleared(self, *, count: object) -> Line:
        return Line("admin.cooldown.all_cleared", {"count": count})

    def cleared(self, *, type: object) -> Line:
        return Line("admin.cooldown.cleared", {"type": type})

    def not_active(self, *, type: object) -> Line:
        return Line("admin.cooldown.not_active", {"type": type})

    def replied_usage(self) -> Line:
        return Line("admin.cooldown.replied_usage", {})

    def unknown_type(self, *, types: object) -> Line:
        return Line("admin.cooldown.unknown_type", {"types": types})

    def usage(self) -> Line:
        return Line("admin.cooldown.usage", {})


class _AdminKaguneDialogs:
    def all_given(self, *, names: object) -> Line:
        return Line("admin.kagune.all_given", {"names": names})

    def give_replied_usage(self, *, types: object) -> Line:
        return Line("admin.kagune.give_replied_usage", {"types": types})

    def give_usage(self, *, types: object) -> Line:
        return Line("admin.kagune.give_usage", {"types": types})

    def given(self, *, kagune: object, strength: object) -> Line:
        return Line("admin.kagune.given", {"kagune": kagune, "strength": strength})

    def remove_replied_usage(self, *, types: object) -> Line:
        return Line("admin.kagune.remove_replied_usage", {"types": types})

    def remove_usage(self, *, types: object) -> Line:
        return Line("admin.kagune.remove_usage", {"types": types})

    def removed(self, *, kagune: object) -> Line:
        return Line("admin.kagune.removed", {"kagune": kagune})

    def unknown_type(self, *, types: object) -> Line:
        return Line("admin.kagune.unknown_type", {"types": types})

    def unknown_type_or_all(self, *, types: object) -> Line:
        return Line("admin.kagune.unknown_type_or_all", {"types": types})


class _AdminKillDialogs:
    def done(self, *, cause: object, deaths: object, id: object) -> Line:
        return Line("admin.kill.done", {"cause": cause, "deaths": deaths, "id": id})

    def usage(self) -> Line:
        return Line("admin.kill.usage", {})


class _AdminLevelUpDialogs:
    def done(
        self,
        *,
        cheston: object,
        level: object,
        notified: object,
        rc: object,
    ) -> Line:
        return Line(
            "admin.level_up.done",
            {
                "cheston": cheston,
                "level": level,
                "notified": notified,
                "rc": rc,
            },
        )

    def usage(self) -> Line:
        return Line("admin.level_up.usage", {})


class _AdminMediaDialogs:
    def did_you_mean(self, *, options: object, target: object) -> Line:
        return Line("admin.media.did_you_mean", {"options": options, "target": target})

    def exists(self) -> Line:
        return Line("admin.media.exists", {})

    def missing_param(self, *, key: object, name: object) -> Line:
        return Line("admin.media.missing_param", {"key": key, "name": name})

    def no_media(self) -> Line:
        return Line("admin.media.no_media", {})

    def remove_not_found(self) -> Line:
        return Line("admin.media.remove_not_found", {})

    def remove_usage(self) -> Line:
        return Line("admin.media.remove_usage", {})

    def removed(self, *, paths: object) -> Line:
        return Line("admin.media.removed", {"paths": paths})

    def saved(self, *, path: object) -> Line:
        return Line("admin.media.saved", {"path": path})

    def section(self, *, keys: object, section: object) -> Line:
        return Line("admin.media.section", {"keys": keys, "section": section})

    def unknown_collection(self, *, collection: object, supported: object) -> Line:
        return Line(
            "admin.media.unknown_collection",
            {
                "collection": collection,
                "supported": supported,
            },
        )

    def unknown_value(
        self,
        *,
        key: object,
        known: object,
        name: object,
        value: object,
    ) -> Line:
        return Line(
            "admin.media.unknown_value",
            {
                "key": key,
                "known": known,
                "name": name,
                "value": value,
            },
        )

    def usage(self) -> Line:
        return Line("admin.media.usage", {})


class _AdminProfileDialogs:
    def active(self) -> Line:
        return Line("admin.profile.active", {})

    def ban(self, *, reason: object, term: object) -> Line:
        return Line("admin.profile.ban", {"reason": reason, "term": term})

    def banned(self) -> Line:
        return Line("admin.profile.banned", {})

    def card(
        self,
        *,
        balance: object,
        ban: object,
        ghoul: object,
        id: object,
        name: object,
        status: object,
        username: object,
    ) -> Line:
        return Line(
            "admin.profile.card",
            {
                "balance": balance,
                "ban": ban,
                "ghoul": ghoul,
                "id": id,
                "name": name,
                "status": status,
                "username": username,
            },
        )

    def ghoul(
        self,
        *,
        dexterity: object,
        health: object,
        hunger: object,
        kakuja: object,
        level: object,
        max_health: object,
        rc: object,
        regeneration: object,
        speed: object,
        strength: object,
    ) -> Line:
        return Line(
            "admin.profile.ghoul",
            {
                "dexterity": dexterity,
                "health": health,
                "hunger": hunger,
                "kakuja": kakuja,
                "level": level,
                "max_health": max_health,
                "rc": rc,
                "regeneration": regeneration,
                "speed": speed,
                "strength": strength,
            },
        )

    def not_found(self) -> Line:
        return Line("admin.profile.not_found", {})

    def usage(self) -> Line:
        return Line("admin.profile.usage", {})


class _AdminProgressDialogs:
    def delta_range(self) -> Line:
        return Line("admin.progress.delta_range", {})

    def done(self, *, levels: object, progress: object) -> Line:
        return Line("admin.progress.done", {"levels": levels, "progress": progress})

    def level(
        self,
        *,
        cheston: object,
        level: object,
        notified: object,
        rc: object,
    ) -> Line:
        return Line(
            "admin.progress.level",
            {
                "cheston": cheston,
                "level": level,
                "notified": notified,
                "rc": rc,
            },
        )

    def replied_usage(self) -> Line:
        return Line("admin.progress.replied_usage", {})

    def usage(self) -> Line:
        return Line("admin.progress.usage", {})


class _AdminResetDialogs:
    def ghoul_deleted(self) -> Line:
        return Line("admin.reset.ghoul_deleted", {})

    def ghoul_done(self, *, id: object) -> Line:
        return Line("admin.reset.ghoul_done", {"id": id})

    def ghoul_missing(self) -> Line:
        return Line("admin.reset.ghoul_missing", {})

    def ghoul_usage(self) -> Line:
        return Line("admin.reset.ghoul_usage", {})

    def no_ghoul(self) -> Line:
        return Line("admin.reset.no_ghoul", {})

    def user_done(self, *, ghoul_deleted: object, id: object) -> Line:
        return Line("admin.reset.user_done", {"ghoul_deleted": ghoul_deleted, "id": id})

    def user_usage(self) -> Line:
        return Line("admin.reset.user_usage", {})


class _AdminRoastDialogs:
    def bad(self) -> Line:
        return Line("admin.roast.bad", {})

    def good(self) -> Line:
        return Line("admin.roast.good", {})

    def not_found(self) -> Line:
        return Line("admin.roast.not_found", {})

    def reset(self, *, count: object) -> Line:
        return Line("admin.roast.reset", {"count": count})

    def usage(self) -> Line:
        return Line("admin.roast.usage", {})


class _AdminStatsDialogs:
    def done(self, *, field: object, target: object, value: object) -> Line:
        return Line(
            "admin.stats.done",
            {
                "field": field,
                "target": target,
                "value": value,
            },
        )

    def no_ghoul(self) -> Line:
        return Line("admin.stats.no_ghoul", {})

    def target_ghoul(self) -> Line:
        return Line("admin.stats.target_ghoul", {})

    def target_user(self) -> Line:
        return Line("admin.stats.target_user", {})

    def unknown_field(self, *, field: object) -> Line:
        return Line("admin.stats.unknown_field", {"field": field})

    def usage(
        self,
        *,
        ghoul_fields: object,
        time_fields: object,
        user_fields: object,
    ) -> Line:
        return Line(
            "admin.stats.usage",
            {
                "ghoul_fields": ghoul_fields,
                "time_fields": time_fields,
                "user_fields": user_fields,
            },
        )


class _AdminUnbanDialogs:
    def done(self, *, id: object, name: object) -> Line:
        return Line("admin.unban.done", {"id": id, "name": name})

    def not_banned(self) -> Line:
        return Line("admin.unban.not_banned", {})

    def usage(self) -> Line:
        return Line("admin.unban.usage", {})


class _AdminDialogs:
    ban = _AdminBanDialogs()
    broadcast = _AdminBroadcastDialogs()
    cooldown = _AdminCooldownDialogs()
    kagune = _AdminKaguneDialogs()
    kill = _AdminKillDialogs()
    level_up = _AdminLevelUpDialogs()
    media = _AdminMediaDialogs()
    profile = _AdminProfileDialogs()
    progress = _AdminProgressDialogs()
    reset = _AdminResetDialogs()
    roast = _AdminRoastDialogs()
    stats = _AdminStatsDialogs()
    unban = _AdminUnbanDialogs()

    def flag_no(self) -> Line:
        return Line("admin.flag_no", {})

    def flag_yes(self) -> Line:
        return Line("admin.flag_yes", {})

    def ghoul_not_found(self) -> Line:
        return Line("admin.ghoul_not_found", {})

    def kagune_already_owned(self, *, kagune: object) -> Line:
        return Line("admin.kagune_already_owned", {"kagune": kagune})

    def kagune_not_owned(self, *, kagune: object) -> Line:
        return Line("admin.kagune_not_owned", {"kagune": kagune})

    def last_kagune(self) -> Line:
        return Line("admin.last_kagune", {})

    def texts_broken(self, *, error: object) -> Line:
        return Line("admin.texts_broken", {"error": error})


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


class _BannedDialogs:
    def forever(self) -> Line:
        return Line("banned.forever", {})

    def no_reason(self) -> Line:
        return Line("banned.no_reason", {})

    def notice(self, *, reason: object, term: object) -> Line:
        return Line("banned.notice", {"reason": reason, "term": term})

    def until(self, *, date: object) -> Line:
        return Line("banned.until", {"date": date})


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


class _CombatPowerRichDialogs:
    def combat_note(self) -> Line:
        return Line("combat_power.rich.combat_note", {})

    def hints(self) -> Line:
        return Line("combat_power.rich.hints", {})

    def title(self, *, danger_rank: object, name: object) -> Line:
        return Line(
            "combat_power.rich.title",
            {
                "danger_rank": danger_rank,
                "name": name,
            },
        )


class _CombatPowerDialogs:
    rich = _CombatPowerRichDialogs()

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


class _DuelButtonsDialogs:
    def consent_initiator(self) -> Line:
        return Line("duel.buttons.consent_initiator", {})

    def consent_target(self) -> Line:
        return Line("duel.buttons.consent_target", {})

    def eat(self) -> Line:
        return Line("duel.buttons.eat", {})

    def handicap(self) -> Line:
        return Line("duel.buttons.handicap", {})

    def release(self) -> Line:
        return Line("duel.buttons.release", {})

    def rob(self) -> Line:
        return Line("duel.buttons.rob", {})

    def serious(self) -> Line:
        return Line("duel.buttons.serious", {})


class _DuelConsentDialogs:
    def accepted(self) -> Line:
        return Line("duel.consent.accepted", {})

    def both_confirmed(self) -> Line:
        return Line("duel.consent.both_confirmed", {})

    def one_confirmed(self) -> Line:
        return Line("duel.consent.one_confirmed", {})

    def stale(self) -> Line:
        return Line("duel.consent.stale", {})

    def timeout(self) -> Line:
        return Line("duel.consent.timeout", {})

    def waiting_favored(self) -> Line:
        return Line("duel.consent.waiting_favored", {})


class _DuelForaDialogs:
    def question(self) -> Line:
        return Line("duel.fora.question", {})

    def starting(self) -> Line:
        return Line("duel.fora.starting", {})


class _DuelOutcomeDialogs:
    def eaten(self, *, loser: object, rc: object, winner: object) -> Line:
        return Line("duel.outcome.eaten", {"loser": loser, "rc": rc, "winner": winner})

    def eaten_nothing(self, *, loser: object, winner: object) -> Line:
        return Line("duel.outcome.eaten_nothing", {"loser": loser, "winner": winner})

    def experience(self, *, progress: object, winner: object) -> Line:
        return Line("duel.outcome.experience", {"progress": progress, "winner": winner})

    def hunger(self, *, restored: object, winner: object) -> Line:
        return Line("duel.outcome.hunger", {"restored": restored, "winner": winner})

    def released(self, *, loser: object, winner: object) -> Line:
        return Line("duel.outcome.released", {"loser": loser, "winner": winner})

    def robbed(self, *, amount: object, loser: object, winner: object) -> Line:
        return Line(
            "duel.outcome.robbed",
            {
                "amount": amount,
                "loser": loser,
                "winner": winner,
            },
        )

    def robbed_nothing(self, *, loser: object, winner: object) -> Line:
        return Line("duel.outcome.robbed_nothing", {"loser": loser, "winner": winner})

    def score(
        self,
        *,
        losses: object,
        name: object,
        total: object,
        wins: object,
    ) -> Line:
        return Line(
            "duel.outcome.score",
            {
                "losses": losses,
                "name": name,
                "total": total,
                "wins": wins,
            },
        )


class _DuelRefusalsDialogs:
    def busy(self) -> Line:
        return Line("duel.refusals.busy", {})

    def claim_failed(self) -> Line:
        return Line("duel.refusals.claim_failed", {})

    def dead(self) -> Line:
        return Line("duel.refusals.dead", {})

    def initiator_day_limit(self, *, per_day: object) -> Line:
        return Line("duel.refusals.initiator_day_limit", {"per_day": per_day})

    def initiator_no_ghoul(self) -> Line:
        return Line("duel.refusals.initiator_no_ghoul", {})

    def initiator_no_private_chat(self) -> Line:
        return Line("duel.refusals.initiator_no_private_chat", {})

    def not_combat_ready(self, *, health: object, threshold: object) -> Line:
        return Line(
            "duel.refusals.not_combat_ready",
            {
                "health": health,
                "threshold": threshold,
            },
        )

    def not_registered(self) -> Line:
        return Line("duel.refusals.not_registered", {})

    def pair_limit(self, *, per_pair: object) -> Line:
        return Line("duel.refusals.pair_limit", {"per_pair": per_pair})

    def self_duel(self) -> Line:
        return Line("duel.refusals.self_duel", {})

    def target_day_limit(self) -> Line:
        return Line("duel.refusals.target_day_limit", {})

    def target_no_ghoul(self) -> Line:
        return Line("duel.refusals.target_no_ghoul", {})

    def target_no_private_chat(self) -> Line:
        return Line("duel.refusals.target_no_private_chat", {})


class _DuelDialogs:
    buttons = _DuelButtonsDialogs()
    consent = _DuelConsentDialogs()
    fora = _DuelForaDialogs()
    outcome = _DuelOutcomeDialogs()
    refusals = _DuelRefusalsDialogs()

    def accepted(self) -> Line:
        return Line("duel.accepted", {})

    def invite(self, *, initiator: object, target: object) -> Line:
        return Line("duel.invite", {"initiator": initiator, "target": target})

    def not_your_button(self) -> Line:
        return Line("duel.not_your_button", {})

    def stale(self) -> Line:
        return Line("duel.stale", {})

    def usage(self) -> Line:
        return Line("duel.usage", {})

    def user_not_found(self, *, target: object) -> Line:
        return Line("duel.user_not_found", {"target": target})


class _EatHumanAmbushDialogs:
    def draw(self) -> Line:
        return Line("eat_human.ambush.draw", {})

    def lost(self) -> Line:
        return Line("eat_human.ambush.lost", {})

    def started(self) -> Line:
        return Line("eat_human.ambush.started", {})

    def won(self, *, rewards: object) -> Line:
        return Line("eat_human.ambush.won", {"rewards": rewards})


class _EatHumanDialogs:
    ambush = _EatHumanAmbushDialogs()

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


class _ErrorsChatTextLengthDialogs:
    def goodbye(self) -> Line:
        return Line("errors.chat_text_length.goodbye", {})

    def rules(self) -> Line:
        return Line("errors.chat_text_length.rules", {})

    def welcome(self) -> Line:
        return Line("errors.chat_text_length.welcome", {})


class _ErrorsQuizDialogs:
    def busy(self, *, seconds: object) -> Line:
        return Line("errors.quiz.busy", {"seconds": seconds})

    def email_missing(self) -> Line:
        return Line("errors.quiz.email_missing", {})

    def session_missing(self, *, email: object) -> Line:
        return Line("errors.quiz.session_missing", {"email": email})


class _ErrorsDialogs:
    chat_text_length = _ErrorsChatTextLengthDialogs()
    quiz = _ErrorsQuizDialogs()

    def cannot_process(self) -> Line:
        return Line("errors.cannot_process", {})

    def chat_not_found(self) -> Line:
        return Line("errors.chat_not_found", {})

    def ghoul_not_found(self) -> Line:
        return Line("errors.ghoul_not_found", {})

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


class _FightLogDialogs:
    def blocked(self, *, icon: object, name: object) -> Line:
        return Line("fight.log.blocked", {"icon": icon, "name": name})

    def fast_hit(self, *, damage: object, icon: object, name: object) -> Line:
        return Line(
            "fight.log.fast_hit",
            {
                "damage": damage,
                "icon": icon,
                "name": name,
            },
        )

    def fast_miss(self, *, icon: object, name: object) -> Line:
        return Line("fight.log.fast_miss", {"icon": icon, "name": name})

    def hit(self, *, damage: object, icon: object, name: object) -> Line:
        return Line("fight.log.hit", {"damage": damage, "icon": icon, "name": name})

    def hp(self, *, chain: object, name: object) -> Line:
        return Line("fight.log.hp", {"chain": chain, "name": name})

    def hp_blocked(self, *, hp: object) -> Line:
        return Line("fight.log.hp_blocked", {"hp": hp})

    def hp_damage(self, *, damage: object, hp: object) -> Line:
        return Line("fight.log.hp_damage", {"damage": damage, "hp": hp})

    def hp_defeated(self, *, chain: object, name: object) -> Line:
        return Line("fight.log.hp_defeated", {"chain": chain, "name": name})

    def hp_regen(self, *, healed: object, hp: object) -> Line:
        return Line("fight.log.hp_regen", {"healed": healed, "hp": hp})

    def hp_unchanged(self, *, hp: object) -> Line:
        return Line("fight.log.hp_unchanged", {"hp": hp})

    def hp_weak_regen(self, *, hp: object) -> Line:
        return Line("fight.log.hp_weak_regen", {"hp": hp})

    def miss(self, *, icon: object, name: object) -> Line:
        return Line("fight.log.miss", {"icon": icon, "name": name})

    def regen(self, *, healed: object, name: object) -> Line:
        return Line("fight.log.regen", {"healed": healed, "name": name})

    def regen_nothing(self, *, name: object) -> Line:
        return Line("fight.log.regen_nothing", {"name": name})

    def round(self, *, number: object) -> Line:
        return Line("fight.log.round", {"number": number})


class _FightDialogs:
    log = _FightLogDialogs()

    def defeated(self, *, name: object) -> Line:
        return Line("fight.defeated", {"name": name})

    def draw(self) -> Line:
        return Line("fight.draw", {})

    def final_hp(self, *, hp: object, name: object) -> Line:
        return Line("fight.final_hp", {"hp": hp, "name": name})

    def lost_on_rounds(self, *, name: object) -> Line:
        return Line("fight.lost_on_rounds", {"name": name})

    def not_ready(self, *, health: object, threshold: object) -> Line:
        return Line("fight.not_ready", {"health": health, "threshold": threshold})

    def rank(self, *, name: object, rank: object) -> Line:
        return Line("fight.rank", {"name": name, "rank": rank})

    def rounds_title(self, *, count: object) -> Line:
        return Line("fight.rounds_title", {"count": count})

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

    def title(self) -> Line:
        return Line("fight.title", {})

    def versus(self) -> Line:
        return Line("fight.versus", {})

    def winner(self, *, name: object) -> Line:
        return Line("fight.winner", {"name": name})


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

    def not_a_ghoul(self) -> Line:
        return Line("ghoul.not_a_ghoul", {})

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


class _KaguneUpgradeChoiceDialogs:
    def button(self, *, kagune: object, price: object) -> Line:
        return Line("kagune.upgrade.choice.button", {"kagune": kagune, "price": price})

    def message(self, *, rows: object) -> Line:
        return Line("kagune.upgrade.choice.message", {"rows": rows})

    def row(self, *, kagune: object, price: object, strength: object) -> Line:
        return Line(
            "kagune.upgrade.choice.row",
            {
                "kagune": kagune,
                "price": price,
                "strength": strength,
            },
        )


class _KaguneUpgradeDialogs:
    choice = _KaguneUpgradeChoiceDialogs()

    def cooldown(self, *, minutes: object, seconds: object) -> Line:
        return Line("kagune.upgrade.cooldown", {"minutes": minutes, "seconds": seconds})

    def done(self, *, kagune: object, kagune_strength: object, money: object) -> Line:
        return Line(
            "kagune.upgrade.done",
            {
                "kagune": kagune,
                "kagune_strength": kagune_strength,
                "money": money,
            },
        )

    def no_ghoul(self) -> Line:
        return Line("kagune.upgrade.no_ghoul", {})

    def no_user(self) -> Line:
        return Line("kagune.upgrade.no_user", {})

    def not_owned(self) -> Line:
        return Line("kagune.upgrade.not_owned", {})

    def unknown_type(self) -> Line:
        return Line("kagune.upgrade.unknown_type", {})


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


class _MobDialogs:
    def busy(self) -> Line:
        return Line("mob.busy", {})

    def cooldown(self, *, minutes: object, seconds: object) -> Line:
        return Line("mob.cooldown", {"minutes": minutes, "seconds": seconds})

    def draw(self) -> Line:
        return Line("mob.draw", {})

    def lost(self) -> Line:
        return Line("mob.lost", {})

    def rc_found(self, *, rc: object) -> Line:
        return Line("mob.rc_found", {"rc": rc})

    def rewards(self, *, cheston: object, progress: object) -> Line:
        return Line("mob.rewards", {"cheston": cheston, "progress": progress})

    def summary(
        self,
        *,
        losses: object,
        outcome: object,
        total: object,
        wins: object,
    ) -> Line:
        return Line(
            "mob.summary",
            {
                "losses": losses,
                "outcome": outcome,
                "total": total,
                "wins": wins,
            },
        )


class _ModerationDialogs:
    def bot_added(self) -> Line:
        return Line("moderation.bot_added", {})

    def goodbye_updated(self, *, text: object) -> Line:
        return Line("moderation.goodbye_updated", {"text": text})

    def rules_updated(self, *, rules: object) -> Line:
        return Line("moderation.rules_updated", {"rules": rules})

    def welcome_updated(self, *, text: object) -> Line:
        return Line("moderation.welcome_updated", {"text": text})


class _NotifyDeathCauseDialogs:
    def admin(self) -> Line:
        return Line("notify.death_cause.admin", {})

    def eaten(self) -> Line:
        return Line("notify.death_cause.eaten", {})

    def starvation(self) -> Line:
        return Line("notify.death_cause.starvation", {})


class _NotifyDialogs:
    death_cause = _NotifyDeathCauseDialogs()

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


class _QuizDialogs:
    def correct(self, *, award: object) -> Line:
        return Line("quiz.correct", {"award": award})

    def not_active(self) -> Line:
        return Line("quiz.not_active", {})

    def play_again(self) -> Line:
        return Line("quiz.play_again", {})

    def result(
        self,
        *,
        answer: object,
        choice: object,
        question: object,
        status: object,
    ) -> Line:
        return Line(
            "quiz.result",
            {
                "answer": answer,
                "choice": choice,
                "question": question,
                "status": status,
            },
        )

    def wrong(self) -> Line:
        return Line("quiz.wrong", {})


class _RoastDialogs:
    def bored(self) -> Line:
        return Line("roast.bored", {})


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


class _StatsShopDialogs:
    def message(self, *, balance: object, rows: object) -> Line:
        return Line("stats.shop.message", {"balance": balance, "rows": rows})

    def row(self, *, current: object, stat: object, x10: object, x5: object) -> Line:
        return Line(
            "stats.shop.row",
            {
                "current": current,
                "stat": stat,
                "x10": x10,
                "x5": x5,
            },
        )


class _StatsDialogs:
    shop = _StatsShopDialogs()

    def bought(self, *, count: object, price: object, stat: object) -> Line:
        return Line("stats.bought", {"count": count, "price": price, "stat": stat})

    def limit(self) -> Line:
        return Line("stats.limit", {})

    def no_money(self) -> Line:
        return Line("stats.no_money", {})

    def private_only(self) -> Line:
        return Line("stats.private_only", {})

    def private_only_action(self) -> Line:
        return Line("stats.private_only_action", {})


class _StatusDialogs:
    def healthy(self) -> Line:
        return Line("status.healthy", {})

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

    def no_regen(self) -> Line:
        return Line("status.no_regen", {})

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

    def starved(self) -> Line:
        return Line("status.starved", {})

    def until_healthy(self, *, duration: object) -> Line:
        return Line("status.until_healthy", {"duration": duration})

    def until_starved(self, *, duration: object) -> Line:
        return Line("status.until_starved", {"duration": duration})


class _TopsBalanceDialogs:
    def bad_count(self) -> Line:
        return Line("tops.balance.bad_count", {})

    def message(self, *, count: object, rows: object) -> Line:
        return Line("tops.balance.message", {"count": count, "rows": rows})

    def row(self, *, balance: object, name: object, place: object) -> Line:
        return Line(
            "tops.balance.row",
            {
                "balance": balance,
                "name": name,
                "place": place,
            },
        )


class _TopsKaguneDialogs:
    def bad_button(self) -> Line:
        return Line("tops.kagune.bad_button", {})

    def sum_button(self) -> Line:
        return Line("tops.kagune.sum_button", {})

    def sum_title(self, *, count: object) -> Line:
        return Line("tops.kagune.sum_title", {"count": count})

    def type_title(self, *, count: object, kagune: object) -> Line:
        return Line("tops.kagune.type_title", {"count": count, "kagune": kagune})


class _TopsDialogs:
    balance = _TopsBalanceDialogs()
    kagune = _TopsKaguneDialogs()

    def empty(self) -> Line:
        return Line("tops.empty", {})

    def list(self, *, rows: object, title: object) -> Line:
        return Line("tops.list", {"rows": rows, "title": title})

    def not_a_number(self) -> Line:
        return Line("tops.not_a_number", {})

    def out_of_range(self) -> Line:
        return Line("tops.out_of_range", {})

    def row(self, *, name: object, place: object, value: object) -> Line:
        return Line("tops.row", {"name": name, "place": place, "value": value})

    def snap_title(self, *, count: object) -> Line:
        return Line("tops.snap_title", {"count": count})

    def unknown_name(self) -> Line:
        return Line("tops.unknown_name", {})


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
    admin = _AdminDialogs()
    anime = _AnimeDialogs()
    banned = _BannedDialogs()
    coffee = _CoffeeDialogs()
    combat_power = _CombatPowerDialogs()
    duel = _DuelDialogs()
    eat_human = _EatHumanDialogs()
    errors = _ErrorsDialogs()
    fight = _FightDialogs()
    fun = _FunDialogs()
    ghoul = _GhoulDialogs()
    kagune = _KaguneDialogs()
    lottery = _LotteryDialogs()
    mob = _MobDialogs()
    moderation = _ModerationDialogs()
    notify = _NotifyDialogs()
    profile = _ProfileDialogs()
    quiz = _QuizDialogs()
    roast = _RoastDialogs()
    rp = _RpDialogs()
    rules = _RulesDialogs()
    snap = _SnapDialogs()
    stats = _StatsDialogs()
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
    "admin.ban.already": frozenset(),
    "admin.ban.done": frozenset({"id", "name", "reason", "term"}),
    "admin.ban.usage": frozenset(),
    "admin.broadcast.all_usage": frozenset(),
    "admin.broadcast.blocked": frozenset(),
    "admin.broadcast.chats_usage": frozenset(),
    "admin.broadcast.finished": frozenset({"failed", "success", "total"}),
    "admin.broadcast.private_usage": frozenset(),
    "admin.broadcast.sent": frozenset(),
    "admin.broadcast.started": frozenset(),
    "admin.broadcast.user_usage": frozenset(),
    "admin.cooldown.all_cleared": frozenset({"count"}),
    "admin.cooldown.cleared": frozenset({"type"}),
    "admin.cooldown.not_active": frozenset({"type"}),
    "admin.cooldown.replied_usage": frozenset(),
    "admin.cooldown.unknown_type": frozenset({"types"}),
    "admin.cooldown.usage": frozenset(),
    "admin.flag_no": frozenset(),
    "admin.flag_yes": frozenset(),
    "admin.ghoul_not_found": frozenset(),
    "admin.kagune.all_given": frozenset({"names"}),
    "admin.kagune.give_replied_usage": frozenset({"types"}),
    "admin.kagune.give_usage": frozenset({"types"}),
    "admin.kagune.given": frozenset({"kagune", "strength"}),
    "admin.kagune.remove_replied_usage": frozenset({"types"}),
    "admin.kagune.remove_usage": frozenset({"types"}),
    "admin.kagune.removed": frozenset({"kagune"}),
    "admin.kagune.unknown_type": frozenset({"types"}),
    "admin.kagune.unknown_type_or_all": frozenset({"types"}),
    "admin.kagune_already_owned": frozenset({"kagune"}),
    "admin.kagune_not_owned": frozenset({"kagune"}),
    "admin.kill.done": frozenset({"cause", "deaths", "id"}),
    "admin.kill.usage": frozenset(),
    "admin.last_kagune": frozenset(),
    "admin.level_up.done": frozenset({"cheston", "level", "notified", "rc"}),
    "admin.level_up.usage": frozenset(),
    "admin.media.did_you_mean": frozenset({"options", "target"}),
    "admin.media.exists": frozenset(),
    "admin.media.missing_param": frozenset({"key", "name"}),
    "admin.media.no_media": frozenset(),
    "admin.media.remove_not_found": frozenset(),
    "admin.media.remove_usage": frozenset(),
    "admin.media.removed": frozenset({"paths"}),
    "admin.media.saved": frozenset({"path"}),
    "admin.media.section": frozenset({"keys", "section"}),
    "admin.media.unknown_collection": frozenset({"collection", "supported"}),
    "admin.media.unknown_value": frozenset({"key", "known", "name", "value"}),
    "admin.media.usage": frozenset(),
    "admin.profile.active": frozenset(),
    "admin.profile.ban": frozenset({"reason", "term"}),
    "admin.profile.banned": frozenset(),
    "admin.profile.card": frozenset(
        {
            "balance",
            "ban",
            "ghoul",
            "id",
            "name",
            "status",
            "username",
        }
    ),
    "admin.profile.ghoul": frozenset(
        {
            "dexterity",
            "health",
            "hunger",
            "kakuja",
            "level",
            "max_health",
            "rc",
            "regeneration",
            "speed",
            "strength",
        }
    ),
    "admin.profile.not_found": frozenset(),
    "admin.profile.usage": frozenset(),
    "admin.progress.delta_range": frozenset(),
    "admin.progress.done": frozenset({"levels", "progress"}),
    "admin.progress.level": frozenset({"cheston", "level", "notified", "rc"}),
    "admin.progress.replied_usage": frozenset(),
    "admin.progress.usage": frozenset(),
    "admin.reset.ghoul_deleted": frozenset(),
    "admin.reset.ghoul_done": frozenset({"id"}),
    "admin.reset.ghoul_missing": frozenset(),
    "admin.reset.ghoul_usage": frozenset(),
    "admin.reset.no_ghoul": frozenset(),
    "admin.reset.user_done": frozenset({"ghoul_deleted", "id"}),
    "admin.reset.user_usage": frozenset(),
    "admin.roast.bad": frozenset(),
    "admin.roast.good": frozenset(),
    "admin.roast.not_found": frozenset(),
    "admin.roast.reset": frozenset({"count"}),
    "admin.roast.usage": frozenset(),
    "admin.stats.done": frozenset({"field", "target", "value"}),
    "admin.stats.no_ghoul": frozenset(),
    "admin.stats.target_ghoul": frozenset(),
    "admin.stats.target_user": frozenset(),
    "admin.stats.unknown_field": frozenset({"field"}),
    "admin.stats.usage": frozenset({"ghoul_fields", "time_fields", "user_fields"}),
    "admin.texts_broken": frozenset({"error"}),
    "admin.unban.done": frozenset({"id", "name"}),
    "admin.unban.not_banned": frozenset(),
    "admin.unban.usage": frozenset(),
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
    "banned.forever": frozenset(),
    "banned.no_reason": frozenset(),
    "banned.notice": frozenset({"reason", "term"}),
    "banned.until": frozenset({"date"}),
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
    "combat_power.rich.combat_note": frozenset(),
    "combat_power.rich.hints": frozenset(),
    "combat_power.rich.title": frozenset({"danger_rank", "name"}),
    "combat_power.short": frozenset({"effective_power", "vacuum_power"}),
    "duel.accepted": frozenset(),
    "duel.buttons.consent_initiator": frozenset(),
    "duel.buttons.consent_target": frozenset(),
    "duel.buttons.eat": frozenset(),
    "duel.buttons.handicap": frozenset(),
    "duel.buttons.release": frozenset(),
    "duel.buttons.rob": frozenset(),
    "duel.buttons.serious": frozenset(),
    "duel.consent.accepted": frozenset(),
    "duel.consent.both_confirmed": frozenset(),
    "duel.consent.one_confirmed": frozenset(),
    "duel.consent.stale": frozenset(),
    "duel.consent.timeout": frozenset(),
    "duel.consent.waiting_favored": frozenset(),
    "duel.fora.question": frozenset(),
    "duel.fora.starting": frozenset(),
    "duel.invite": frozenset({"initiator", "target"}),
    "duel.not_your_button": frozenset(),
    "duel.outcome.eaten": frozenset({"loser", "rc", "winner"}),
    "duel.outcome.eaten_nothing": frozenset({"loser", "winner"}),
    "duel.outcome.experience": frozenset({"progress", "winner"}),
    "duel.outcome.hunger": frozenset({"restored", "winner"}),
    "duel.outcome.released": frozenset({"loser", "winner"}),
    "duel.outcome.robbed": frozenset({"amount", "loser", "winner"}),
    "duel.outcome.robbed_nothing": frozenset({"loser", "winner"}),
    "duel.outcome.score": frozenset({"losses", "name", "total", "wins"}),
    "duel.refusals.busy": frozenset(),
    "duel.refusals.claim_failed": frozenset(),
    "duel.refusals.dead": frozenset(),
    "duel.refusals.initiator_day_limit": frozenset({"per_day"}),
    "duel.refusals.initiator_no_ghoul": frozenset(),
    "duel.refusals.initiator_no_private_chat": frozenset(),
    "duel.refusals.not_combat_ready": frozenset({"health", "threshold"}),
    "duel.refusals.not_registered": frozenset(),
    "duel.refusals.pair_limit": frozenset({"per_pair"}),
    "duel.refusals.self_duel": frozenset(),
    "duel.refusals.target_day_limit": frozenset(),
    "duel.refusals.target_no_ghoul": frozenset(),
    "duel.refusals.target_no_private_chat": frozenset(),
    "duel.stale": frozenset(),
    "duel.usage": frozenset(),
    "duel.user_not_found": frozenset({"target"}),
    "eat_human.ambush.draw": frozenset(),
    "eat_human.ambush.lost": frozenset(),
    "eat_human.ambush.started": frozenset(),
    "eat_human.ambush.won": frozenset({"rewards"}),
    "eat_human.cooldown": frozenset({"hours", "minutes", "seconds"}),
    "eat_human.done": frozenset({"count", "hunger", "restored"}),
    "errors.cannot_process": frozenset(),
    "errors.chat_not_found": frozenset(),
    "errors.chat_text_length.goodbye": frozenset(),
    "errors.chat_text_length.rules": frozenset(),
    "errors.chat_text_length.welcome": frozenset(),
    "errors.ghoul_not_found": frozenset(),
    "errors.media_not_found": frozenset(),
    "errors.not_enough_money": frozenset({"money"}),
    "errors.quiz.busy": frozenset({"seconds"}),
    "errors.quiz.email_missing": frozenset(),
    "errors.quiz.session_missing": frozenset({"email"}),
    "errors.unexpected": frozenset({"error"}),
    "errors.user_not_found": frozenset({"query"}),
    "errors.username_not_found": frozenset({"username"}),
    "fight.defeated": frozenset({"name"}),
    "fight.draw": frozenset(),
    "fight.final_hp": frozenset({"hp", "name"}),
    "fight.log.blocked": frozenset({"icon", "name"}),
    "fight.log.fast_hit": frozenset({"damage", "icon", "name"}),
    "fight.log.fast_miss": frozenset({"icon", "name"}),
    "fight.log.hit": frozenset({"damage", "icon", "name"}),
    "fight.log.hp": frozenset({"chain", "name"}),
    "fight.log.hp_blocked": frozenset({"hp"}),
    "fight.log.hp_damage": frozenset({"damage", "hp"}),
    "fight.log.hp_defeated": frozenset({"chain", "name"}),
    "fight.log.hp_regen": frozenset({"healed", "hp"}),
    "fight.log.hp_unchanged": frozenset({"hp"}),
    "fight.log.hp_weak_regen": frozenset({"hp"}),
    "fight.log.miss": frozenset({"icon", "name"}),
    "fight.log.regen": frozenset({"healed", "name"}),
    "fight.log.regen_nothing": frozenset({"name"}),
    "fight.log.round": frozenset({"number"}),
    "fight.lost_on_rounds": frozenset({"name"}),
    "fight.not_ready": frozenset({"health", "threshold"}),
    "fight.rank": frozenset({"name", "rank"}),
    "fight.rounds_title": frozenset({"count"}),
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
    "fight.title": frozenset(),
    "fight.versus": frozenset(),
    "fight.winner": frozenset({"name"}),
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
    "ghoul.not_a_ghoul": frozenset(),
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
    "kagune.upgrade.choice.button": frozenset({"kagune", "price"}),
    "kagune.upgrade.choice.message": frozenset({"rows"}),
    "kagune.upgrade.choice.row": frozenset({"kagune", "price", "strength"}),
    "kagune.upgrade.cooldown": frozenset({"minutes", "seconds"}),
    "kagune.upgrade.done": frozenset({"kagune", "kagune_strength", "money"}),
    "kagune.upgrade.no_ghoul": frozenset(),
    "kagune.upgrade.no_user": frozenset(),
    "kagune.upgrade.not_owned": frozenset(),
    "kagune.upgrade.unknown_type": frozenset(),
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
    "mob.busy": frozenset(),
    "mob.cooldown": frozenset({"minutes", "seconds"}),
    "mob.draw": frozenset(),
    "mob.lost": frozenset(),
    "mob.rc_found": frozenset({"rc"}),
    "mob.rewards": frozenset({"cheston", "progress"}),
    "mob.summary": frozenset({"losses", "outcome", "total", "wins"}),
    "moderation.bot_added": frozenset(),
    "moderation.goodbye_updated": frozenset({"text"}),
    "moderation.rules_updated": frozenset({"rules"}),
    "moderation.welcome_updated": frozenset({"text"}),
    "notify.death": frozenset({"cause", "level", "lifetime_rc_earned"}),
    "notify.death_cause.admin": frozenset(),
    "notify.death_cause.eaten": frozenset(),
    "notify.death_cause.starvation": frozenset(),
    "notify.health_full": frozenset(),
    "notify.hunger": frozenset({"threshold"}),
    "notify.level_up": frozenset({"cheston", "level", "rc", "stat_changes"}),
    "profile.card": frozenset({"balance", "name", "race"}),
    "profile.unknown_race": frozenset(),
    "quiz.correct": frozenset({"award"}),
    "quiz.not_active": frozenset(),
    "quiz.play_again": frozenset(),
    "quiz.result": frozenset({"answer", "choice", "question", "status"}),
    "quiz.wrong": frozenset(),
    "roast.bored": frozenset(),
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
    "stats.bought": frozenset({"count", "price", "stat"}),
    "stats.limit": frozenset(),
    "stats.no_money": frozenset(),
    "stats.private_only": frozenset(),
    "stats.private_only_action": frozenset(),
    "stats.shop.message": frozenset({"balance", "rows"}),
    "stats.shop.row": frozenset({"current", "stat", "x10", "x5"}),
    "status.healthy": frozenset(),
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
    "status.no_regen": frozenset(),
    "status.regen": frozenset({"health", "hp_per_hour", "max_health", "time_left"}),
    "status.starved": frozenset(),
    "status.until_healthy": frozenset({"duration"}),
    "status.until_starved": frozenset({"duration"}),
    "tops.balance.bad_count": frozenset(),
    "tops.balance.message": frozenset({"count", "rows"}),
    "tops.balance.row": frozenset({"balance", "name", "place"}),
    "tops.empty": frozenset(),
    "tops.kagune.bad_button": frozenset(),
    "tops.kagune.sum_button": frozenset(),
    "tops.kagune.sum_title": frozenset({"count"}),
    "tops.kagune.type_title": frozenset({"count", "kagune"}),
    "tops.list": frozenset({"rows", "title"}),
    "tops.not_a_number": frozenset(),
    "tops.out_of_range": frozenset(),
    "tops.row": frozenset({"name", "place", "value"}),
    "tops.snap_title": frozenset({"count"}),
    "tops.unknown_name": frozenset(),
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
