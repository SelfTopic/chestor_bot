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


class _AdminPromoCardDialogs:
    def activations(self) -> Line:
        return Line("admin.promo.card.activations", {})

    def activations_value(self, *, limit: object, used: object) -> Line:
        return Line(
            "admin.promo.card.activations_value",
            {
                "limit": limit,
                "used": used,
            },
        )

    def back_button(self) -> Line:
        return Line("admin.promo.card.back_button", {})

    def cancel_button(self) -> Line:
        return Line("admin.promo.card.cancel_button", {})

    def column_field(self) -> Line:
        return Line("admin.promo.card.column_field", {})

    def column_value(self) -> Line:
        return Line("admin.promo.card.column_value", {})

    def confirm_button(self) -> Line:
        return Line("admin.promo.card.confirm_button", {})

    def confirm_question(self) -> Line:
        return Line("admin.promo.card.confirm_question", {})

    def created(self) -> Line:
        return Line("admin.promo.card.created", {})

    def delete_button(self) -> Line:
        return Line("admin.promo.card.delete_button", {})

    def deleted(self) -> Line:
        return Line("admin.promo.card.deleted", {})

    def expired_at(self, *, date: object) -> Line:
        return Line("admin.promo.card.expired_at", {"date": date})

    def gone(self) -> Line:
        return Line("admin.promo.card.gone", {})

    def not_found(self, *, name: object) -> Line:
        return Line("admin.promo.card.not_found", {"name": name})

    def rewards(self) -> Line:
        return Line("admin.promo.card.rewards", {})

    def status(self) -> Line:
        return Line("admin.promo.card.status", {})

    def term(self) -> Line:
        return Line("admin.promo.card.term", {})

    def title(self, *, name: object) -> Line:
        return Line("admin.promo.card.title", {"name": name})

    def until(self, *, date: object, left: object) -> Line:
        return Line("admin.promo.card.until", {"date": date, "left": left})

    def usage(self) -> Line:
        return Line("admin.promo.card.usage", {})

    def who_when(self, *, date: object, who: object) -> Line:
        return Line("admin.promo.card.who_when", {"date": date, "who": who})


class _AdminPromoCatalogDialogs:
    def column_activations(self) -> Line:
        return Line("admin.promo.catalog.column_activations", {})

    def column_name(self) -> Line:
        return Line("admin.promo.catalog.column_name", {})

    def column_status(self) -> Line:
        return Line("admin.promo.catalog.column_status", {})

    def column_term(self) -> Line:
        return Line("admin.promo.catalog.column_term", {})

    def empty(self) -> Line:
        return Line("admin.promo.catalog.empty", {})

    def term_until(self, *, date: object) -> Line:
        return Line("admin.promo.catalog.term_until", {"date": date})

    def title(self) -> Line:
        return Line("admin.promo.catalog.title", {})


class _AdminPromoStatusDialogs:
    def active(self) -> Line:
        return Line("admin.promo.status.active", {})

    def deleted(self) -> Line:
        return Line("admin.promo.status.deleted", {})

    def exhausted(self) -> Line:
        return Line("admin.promo.status.exhausted", {})

    def expired(self) -> Line:
        return Line("admin.promo.status.expired", {})


class _AdminPromoDialogs:
    card = _AdminPromoCardDialogs()
    catalog = _AdminPromoCatalogDialogs()
    status = _AdminPromoStatusDialogs()

    def bad_line(self, *, line: object) -> Line:
        return Line("admin.promo.bad_line", {"line": line})

    def created(
        self,
        *,
        activations: object,
        name: object,
        rewards: object,
        until: object,
    ) -> Line:
        return Line(
            "admin.promo.created",
            {
                "activations": activations,
                "name": name,
                "rewards": rewards,
                "until": until,
            },
        )

    def forever(self) -> Line:
        return Line("admin.promo.forever", {})

    def name_taken(self, *, name: object) -> Line:
        return Line("admin.promo.name_taken", {"name": name})

    def until(self, *, date: object) -> Line:
        return Line("admin.promo.until", {"date": date})

    def usage(self) -> Line:
        return Line("admin.promo.usage", {})


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


class _AdminServiceDialogs:
    def marked(self, *, id: object) -> Line:
        return Line("admin.service.marked", {"id": id})

    def unmark_usage(self) -> Line:
        return Line("admin.service.unmark_usage", {})

    def unmarked(self, *, id: object) -> Line:
        return Line("admin.service.unmarked", {"id": id})

    def usage(self) -> Line:
        return Line("admin.service.usage", {})


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
    promo = _AdminPromoDialogs()
    reset = _AdminResetDialogs()
    roast = _AdminRoastDialogs()
    service = _AdminServiceDialogs()
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
    def column_hunger(self) -> Line:
        return Line("combat_power.rich.column_hunger", {})

    def column_kagune(self) -> Line:
        return Line("combat_power.rich.column_kagune", {})

    def column_stat(self) -> Line:
        return Line("combat_power.rich.column_stat", {})

    def column_value(self) -> Line:
        return Line("combat_power.rich.column_value", {})

    def combat_note(self) -> Line:
        return Line("combat_power.rich.combat_note", {})

    def hints(self) -> Line:
        return Line("combat_power.rich.hints", {})

    def kagune_row(self) -> Line:
        return Line("combat_power.rich.kagune_row", {})

    def title(self, *, danger_rank: object, name: object) -> Line:
        return Line(
            "combat_power.rich.title",
            {
                "danger_rank": danger_rank,
                "name": name,
            },
        )

    def total_row(self) -> Line:
        return Line("combat_power.rich.total_row", {})


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


class _DivorceDialogs:
    def ask(self) -> Line:
        return Line("divorce.ask", {})

    def button(self) -> Line:
        return Line("divorce.button", {})

    def dissolved(self, *, amount: object, heir: object, name: object) -> Line:
        return Line("divorce.dissolved", {"amount": amount, "heir": heir, "name": name})

    def done(self, *, name: object) -> Line:
        return Line("divorce.done", {"name": name})

    def not_married(self) -> Line:
        return Line("divorce.not_married", {})

    def stale(self) -> Line:
        return Line("divorce.stale", {})


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

    def spouses(self) -> Line:
        return Line("duel.refusals.spouses", {})

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

    def not_enough_rc(self, *, rc: object) -> Line:
        return Line("errors.not_enough_rc", {"rc": rc})

    def unexpected(self, *, error: object) -> Line:
        return Line("errors.unexpected", {"error": error})

    def user_not_found(self, *, query: object) -> Line:
        return Line("errors.user_not_found", {"query": query})

    def username_not_found(self, *, username: object) -> Line:
        return Line("errors.username_not_found", {"username": username})


class _FamilyListDialogs:
    def empty(self) -> Line:
        return Line("family.list.empty", {})

    def message(self, *, count: object, rows: object) -> Line:
        return Line("family.list.message", {"count": count, "rows": rows})

    def more(self, *, count: object) -> Line:
        return Line("family.list.more", {"count": count})

    def named_row(
        self,
        *,
        age: object,
        members: object,
        name: object,
        place: object,
        since: object,
    ) -> Line:
        return Line(
            "family.list.named_row",
            {
                "age": age,
                "members": members,
                "name": name,
                "place": place,
                "since": since,
            },
        )

    def row(
        self,
        *,
        age: object,
        members: object,
        place: object,
        since: object,
    ) -> Line:
        return Line(
            "family.list.row",
            {
                "age": age,
                "members": members,
                "place": place,
                "since": since,
            },
        )


class _FamilyRenameButtonsDialogs:
    def agree(self) -> Line:
        return Line("family.rename.buttons.agree", {})

    def decline(self) -> Line:
        return Line("family.rename.buttons.decline", {})

    def private(self) -> Line:
        return Line("family.rename.buttons.private", {})


class _FamilyRenameConsentDialogs:
    def accepted(self) -> Line:
        return Line("family.rename.consent.accepted", {})

    def declined(self) -> Line:
        return Line("family.rename.consent.declined", {})

    def renamed(self) -> Line:
        return Line("family.rename.consent.renamed", {})


class _FamilyRenameRefusalsDialogs:
    def already_pending(self) -> Line:
        return Line("family.rename.refusals.already_pending", {})

    def bad_name(self, *, limit: object) -> Line:
        return Line("family.rename.refusals.bad_name", {"limit": limit})

    def not_married(self) -> Line:
        return Line("family.rename.refusals.not_married", {})


class _FamilyRenameDialogs:
    buttons = _FamilyRenameButtonsDialogs()
    consent = _FamilyRenameConsentDialogs()
    refusals = _FamilyRenameRefusalsDialogs()

    def ask(self, *, name: object, proposer: object, rows: object) -> Line:
        return Line(
            "family.rename.ask",
            {
                "name": name,
                "proposer": proposer,
                "rows": rows,
            },
        )

    def declined(self, *, name: object, person: object) -> Line:
        return Line("family.rename.declined", {"name": name, "person": person})

    def declined_private(self) -> Line:
        return Line("family.rename.declined_private", {})

    def expired(self, *, name: object) -> Line:
        return Line("family.rename.expired", {"name": name})

    def link_not_family(self) -> Line:
        return Line("family.rename.link_not_family", {})

    def link_stale(self) -> Line:
        return Line("family.rename.link_stale", {})

    def renamed(self, *, name: object) -> Line:
        return Line("family.rename.renamed", {"name": name})

    def usage(self) -> Line:
        return Line("family.rename.usage", {})

    def vote(self, *, name: object) -> Line:
        return Line("family.rename.vote", {"name": name})

    def voted(self) -> Line:
        return Line("family.rename.voted", {})


class _FamilyDialogs:
    list = _FamilyListDialogs()
    rename = _FamilyRenameDialogs()

    def row(self, *, age: object, name: object, since: object) -> Line:
        return Line("family.row", {"age": age, "name": name, "since": since})

    def single(self) -> Line:
        return Line("family.single", {})

    def title(self) -> Line:
        return Line("family.title", {})

    def title_named(self, *, name: object) -> Line:
        return Line("family.title_named", {"name": name})

    def top_name(self, *, members: object) -> Line:
        return Line("family.top_name", {"members": members})

    def view(self, *, balance: object, rows: object, title: object) -> Line:
        return Line("family.view", {"balance": balance, "rows": rows, "title": title})


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


class _FunEditsDialogs:
    def empty(self) -> Line:
        return Line("fun.edits.empty", {})


class _FunPickDialogs:
    def result(self, *, choice: object) -> Line:
        return Line("fun.pick.result", {"choice": choice})

    def too_few(self) -> Line:
        return Line("fun.pick.too_few", {})

    def too_long(self) -> Line:
        return Line("fun.pick.too_long", {})

    def too_many(self, *, max_items: object) -> Line:
        return Line("fun.pick.too_many", {"max_items": max_items})


class _FunQuoteDialogs:
    def not_found(self) -> Line:
        return Line("fun.quote.not_found", {})


class _FunSearchDialogs:
    def cooldown(self, *, seconds: object) -> Line:
        return Line("fun.search.cooldown", {"seconds": seconds})

    def failed(self) -> Line:
        return Line("fun.search.failed", {})

    def limit_reached(self) -> Line:
        return Line("fun.search.limit_reached", {})

    def unavailable(self) -> Line:
        return Line("fun.search.unavailable", {})

    def usage(self) -> Line:
        return Line("fun.search.usage", {})


class _FunDialogs:
    calculator = _FunCalculatorDialogs()
    edits = _FunEditsDialogs()
    pick = _FunPickDialogs()
    quote = _FunQuoteDialogs()
    search = _FunSearchDialogs()

    def nobody(self) -> Line:
        return Line("fun.nobody", {})

    def number(self, *, number: object) -> Line:
        return Line("fun.number", {"number": number})

    def random_participant(self, *, mention: object) -> Line:
        return Line("fun.random_participant", {"mention": mention})

    def who(self, *, mention: object, question: object) -> Line:
        return Line("fun.who", {"mention": mention, "question": question})


class _GhoulRichProfileDialogs:
    def coffee(self, *, count: object) -> Line:
        return Line("ghoul.rich_profile.coffee", {"count": count})

    def deaths(self, *, count: object) -> Line:
        return Line("ghoul.rich_profile.deaths", {"count": count})

    def fights(self, *, losses: object, total: object, wins: object) -> Line:
        return Line(
            "ghoul.rich_profile.fights",
            {
                "losses": losses,
                "total": total,
                "wins": wins,
            },
        )

    def ghouls(self, *, count: object) -> Line:
        return Line("ghoul.rich_profile.ghouls", {"count": count})

    def health(self, *, health: object, max_health: object) -> Line:
        return Line(
            "ghoul.rich_profile.health",
            {
                "health": health,
                "max_health": max_health,
            },
        )

    def humans(self, *, count: object) -> Line:
        return Line("ghoul.rich_profile.humans", {"count": count})

    def hunger(self, *, hunger: object, tier: object) -> Line:
        return Line("ghoul.rich_profile.hunger", {"hunger": hunger, "tier": tier})

    def kagune_row(self, *, kagune: object, strength: object) -> Line:
        return Line(
            "ghoul.rich_profile.kagune_row",
            {
                "kagune": kagune,
                "strength": strength,
            },
        )

    def kagune_types(self) -> Line:
        return Line("ghoul.rich_profile.kagune_types", {})

    def kakuja(self, *, status: object) -> Line:
        return Line("ghoul.rich_profile.kakuja", {"status": status})

    def kakuja_no(self) -> Line:
        return Line("ghoul.rich_profile.kakuja_no", {})

    def kakuja_yes(self) -> Line:
        return Line("ghoul.rich_profile.kakuja_yes", {})

    def level(self, *, level: object) -> Line:
        return Line("ghoul.rich_profile.level", {"level": level})

    def mob_fights(self, *, losses: object, total: object, wins: object) -> Line:
        return Line(
            "ghoul.rich_profile.mob_fights",
            {
                "losses": losses,
                "total": total,
                "wins": wins,
            },
        )

    def power(self, *, power: object) -> Line:
        return Line("ghoul.rich_profile.power", {"power": power})

    def rc(self, *, rc: object) -> Line:
        return Line("ghoul.rich_profile.rc", {"rc": rc})

    def snaps(self, *, count: object) -> Line:
        return Line("ghoul.rich_profile.snaps", {"count": count})

    def stat_row(self, *, stat: object, value: object) -> Line:
        return Line("ghoul.rich_profile.stat_row", {"stat": stat, "value": value})

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


class _HelpDialogs:
    def did_you_mean(self, *, query: object) -> Line:
        return Line("help.did_you_mean", {"query": query})

    def more(self) -> Line:
        return Line("help.more", {})

    def not_found(self, *, query: object) -> Line:
        return Line("help.not_found", {"query": query})

    def sections(self, *, rows: object) -> Line:
        return Line("help.sections", {"rows": rows})


class _KaguneEvolutionDialogs:
    def all_kagune_done(self) -> Line:
        return Line("kagune.evolution.all_kagune_done", {})

    def already_kakuja(self) -> Line:
        return Line("kagune.evolution.already_kakuja", {})

    def buy_kagune_button(self, *, cheston: object, kagune: object, rc: object) -> Line:
        return Line(
            "kagune.evolution.buy_kagune_button",
            {
                "cheston": cheston,
                "kagune": kagune,
                "rc": rc,
            },
        )

    def buy_kakuja_button(self, *, cheston: object, rc: object) -> Line:
        return Line(
            "kagune.evolution.buy_kakuja_button",
            {
                "cheston": cheston,
                "rc": rc,
            },
        )

    def column_status(self) -> Line:
        return Line("kagune.evolution.column_status", {})

    def column_type(self) -> Line:
        return Line("kagune.evolution.column_type", {})

    def kagune_done(
        self,
        *,
        cheston: object,
        kagune: object,
        rc: object,
        strength: object,
    ) -> Line:
        return Line(
            "kagune.evolution.kagune_done",
            {
                "cheston": cheston,
                "kagune": kagune,
                "rc": rc,
                "strength": strength,
            },
        )

    def kakuja_done(self, *, cheston: object, rc: object) -> Line:
        return Line("kagune.evolution.kakuja_done", {"cheston": cheston, "rc": rc})

    def kakuja_no(self) -> Line:
        return Line("kagune.evolution.kakuja_no", {})

    def kakuja_row(self) -> Line:
        return Line("kagune.evolution.kakuja_row", {})

    def kakuja_yes(self) -> Line:
        return Line("kagune.evolution.kakuja_yes", {})

    def not_owned(self) -> Line:
        return Line("kagune.evolution.not_owned", {})

    def owned(self, *, strength: object) -> Line:
        return Line("kagune.evolution.owned", {"strength": strength})

    def title(self) -> Line:
        return Line("kagune.evolution.title", {})

    def warning(self) -> Line:
        return Line("kagune.evolution.warning", {})


class _KaguneGuideDialogs:
    def column_type(self) -> Line:
        return Line("kagune.guide.column_type", {})

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
    evolution = _KaguneEvolutionDialogs()
    guide = _KaguneGuideDialogs()
    upgrade = _KaguneUpgradeDialogs()

    def info(self) -> Line:
        return Line("kagune.info", {})


class _LinkMediaDialogs:
    def too_large(self) -> Line:
        return Line("link_media.too_large", {})


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


class _MarriageButtonsDialogs:
    def decline(self) -> Line:
        return Line("marriage.buttons.decline", {})

    def family(self) -> Line:
        return Line("marriage.buttons.family", {})

    def family_decline(self) -> Line:
        return Line("marriage.buttons.family_decline", {})

    def family_vote(self) -> Line:
        return Line("marriage.buttons.family_vote", {})

    def pay(self, *, price: object) -> Line:
        return Line("marriage.buttons.pay", {"price": price})

    def proposer(self) -> Line:
        return Line("marriage.buttons.proposer", {})

    def target(self) -> Line:
        return Line("marriage.buttons.target", {})


class _MarriageConsentDialogs:
    def accepted(self) -> Line:
        return Line("marriage.consent.accepted", {})

    def already(self) -> Line:
        return Line("marriage.consent.already", {})

    def declined(self) -> Line:
        return Line("marriage.consent.declined", {})

    def married(self) -> Line:
        return Line("marriage.consent.married", {})

    def not_enough_money(self, *, price: object) -> Line:
        return Line("marriage.consent.not_enough_money", {"price": price})

    def not_invited(self) -> Line:
        return Line("marriage.consent.not_invited", {})

    def stale(self) -> Line:
        return Line("marriage.consent.stale", {})


class _MarriageFailedDialogs:
    def family_changed(self, *, proposer: object) -> Line:
        return Line("marriage.failed.family_changed", {"proposer": proposer})

    def target_broke(self, *, price: object, target: object) -> Line:
        return Line("marriage.failed.target_broke", {"price": price, "target": target})

    def target_taken(self, *, target: object) -> Line:
        return Line("marriage.failed.target_taken", {"target": target})


class _MarriageRefusalsDialogs:
    def already_proposed(self) -> Line:
        return Line("marriage.refusals.already_proposed", {})

    def bot(self) -> Line:
        return Line("marriage.refusals.bot", {})

    def not_a_person(self) -> Line:
        return Line("marriage.refusals.not_a_person", {})

    def not_enough_money(self, *, price: object) -> Line:
        return Line("marriage.refusals.not_enough_money", {"price": price})

    def not_registered(self) -> Line:
        return Line("marriage.refusals.not_registered", {})

    def same_family(self) -> Line:
        return Line("marriage.refusals.same_family", {})

    def self(self) -> Line:
        return Line("marriage.refusals.self", {})

    def target_married(self) -> Line:
        return Line("marriage.refusals.target_married", {})


class _MarriageDialogs:
    buttons = _MarriageButtonsDialogs()
    consent = _MarriageConsentDialogs()
    failed = _MarriageFailedDialogs()
    refusals = _MarriageRefusalsDialogs()

    def ask(self, *, price: object, proposer: object, target: object) -> Line:
        return Line(
            "marriage.ask",
            {
                "price": price,
                "proposer": proposer,
                "target": target,
            },
        )

    def declined(self, *, name: object, price: object, proposer: object) -> Line:
        return Line(
            "marriage.declined",
            {
                "name": name,
                "price": price,
                "proposer": proposer,
            },
        )

    def expired(self, *, price: object, proposer: object) -> Line:
        return Line("marriage.expired", {"price": price, "proposer": proposer})

    def family_declined(self) -> Line:
        return Line("marriage.family_declined", {})

    def family_hint(self, *, proposer: object) -> Line:
        return Line("marriage.family_hint", {"proposer": proposer})

    def family_vote(self, *, proposer: object, target: object) -> Line:
        return Line("marriage.family_vote", {"proposer": proposer, "target": target})

    def family_voted(self) -> Line:
        return Line("marriage.family_voted", {})

    def invite(self, *, proposer: object, rows: object, target: object) -> Line:
        return Line(
            "marriage.invite",
            {
                "proposer": proposer,
                "rows": rows,
                "target": target,
            },
        )

    def link_not_family(self) -> Line:
        return Line("marriage.link_not_family", {})

    def link_stale(self) -> Line:
        return Line("marriage.link_stale", {})

    def married(self, *, members: object, target: object) -> Line:
        return Line("marriage.married", {"members": members, "target": target})

    def not_your_button(self) -> Line:
        return Line("marriage.not_your_button", {})

    def row_confirmed(self, *, name: object) -> Line:
        return Line("marriage.row_confirmed", {"name": name})

    def row_waiting(self, *, name: object) -> Line:
        return Line("marriage.row_waiting", {"name": name})

    def usage(self) -> Line:
        return Line("marriage.usage", {})

    def user_not_found(self, *, target: object) -> Line:
        return Line("marriage.user_not_found", {"target": target})


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


class _ModerationFeatureDialogs:
    def ban(self) -> Line:
        return Line("moderation.feature.ban", {})

    def kick(self) -> Line:
        return Line("moderation.feature.kick", {})

    def mute(self) -> Line:
        return Line("moderation.feature.mute", {})

    def notices(self) -> Line:
        return Line("moderation.feature.notices", {})

    def warns(self) -> Line:
        return Line("moderation.feature.warns", {})


class _ModerationMenuDialogs:
    def admin_chat(self) -> Line:
        return Line("moderation.menu.admin_chat", {})

    def admin_chat_none(self) -> Line:
        return Line("moderation.menu.admin_chat_none", {})

    def ban(self) -> Line:
        return Line("moderation.menu.ban", {})

    def ban_default(self) -> Line:
        return Line("moderation.menu.ban_default", {})

    def button_minus(self) -> Line:
        return Line("moderation.menu.button_minus", {})

    def button_next(self) -> Line:
        return Line("moderation.menu.button_next", {})

    def button_off(self, *, name: object) -> Line:
        return Line("moderation.menu.button_off", {"name": name})

    def button_on(self, *, name: object) -> Line:
        return Line("moderation.menu.button_on", {"name": name})

    def button_plus(self) -> Line:
        return Line("moderation.menu.button_plus", {})

    def button_prev(self) -> Line:
        return Line("moderation.menu.button_prev", {})

    def button_value(self, *, name: object, value: object) -> Line:
        return Line("moderation.menu.button_value", {"name": name, "value": value})

    def column_setting(self) -> Line:
        return Line("moderation.menu.column_setting", {})

    def column_value(self) -> Line:
        return Line("moderation.menu.column_value", {})

    def hint(self) -> Line:
        return Line("moderation.menu.hint", {})

    def kick(self) -> Line:
        return Line("moderation.menu.kick", {})

    def mute(self) -> Line:
        return Line("moderation.menu.mute", {})

    def mute_default(self) -> Line:
        return Line("moderation.menu.mute_default", {})

    def no_right(self, *, right: object) -> Line:
        return Line("moderation.menu.no_right", {"right": right})

    def not_admin(self) -> Line:
        return Line("moderation.menu.not_admin", {})

    def notices(self) -> Line:
        return Line("moderation.menu.notices", {})

    def off(self) -> Line:
        return Line("moderation.menu.off", {})

    def on(self) -> Line:
        return Line("moderation.menu.on", {})

    def title(self, *, chat: object) -> Line:
        return Line("moderation.menu.title", {"chat": chat})

    def use_arrows(self) -> Line:
        return Line("moderation.menu.use_arrows", {})

    def voice(self) -> Line:
        return Line("moderation.menu.voice", {})

    def voice_neutral(self) -> Line:
        return Line("moderation.menu.voice_neutral", {})

    def voice_rough(self) -> Line:
        return Line("moderation.menu.voice_rough", {})

    def warn_expiry(self) -> Line:
        return Line("moderation.menu.warn_expiry", {})

    def warn_limit(self) -> Line:
        return Line("moderation.menu.warn_limit", {})

    def warn_penalty(self) -> Line:
        return Line("moderation.menu.warn_penalty", {})

    def warns(self) -> Line:
        return Line("moderation.menu.warns", {})


class _ModerationNeutralDialogs:
    def admin_chat_current(self, *, chat: object) -> Line:
        return Line("moderation.neutral.admin_chat_current", {"chat": chat})

    def admin_chat_linked(self, *, chat: object) -> Line:
        return Line("moderation.neutral.admin_chat_linked", {"chat": chat})

    def admin_chat_none(self) -> Line:
        return Line("moderation.neutral.admin_chat_none", {})

    def admin_chat_not_found(self, *, query: object) -> Line:
        return Line("moderation.neutral.admin_chat_not_found", {"query": query})

    def admin_chat_not_linked(self) -> Line:
        return Line("moderation.neutral.admin_chat_not_linked", {})

    def admin_chat_requested(self, *, chat: object, command: object) -> Line:
        return Line(
            "moderation.neutral.admin_chat_requested",
            {
                "chat": chat,
                "command": command,
            },
        )

    def admin_chat_self(self) -> Line:
        return Line("moderation.neutral.admin_chat_self", {})

    def admin_chat_taken(self) -> Line:
        return Line("moderation.neutral.admin_chat_taken", {})

    def admin_chat_unlinked(self, *, chat: object) -> Line:
        return Line("moderation.neutral.admin_chat_unlinked", {"chat": chat})

    def anonymous(self) -> Line:
        return Line("moderation.neutral.anonymous", {})

    def ban_default_current(self, *, term: object) -> Line:
        return Line("moderation.neutral.ban_default_current", {"term": term})

    def ban_default_set(self, *, term: object) -> Line:
        return Line("moderation.neutral.ban_default_set", {"term": term})

    def ban_usage(self) -> Line:
        return Line("moderation.neutral.ban_usage", {})

    def banned(self, *, name: object, term: object) -> Line:
        return Line("moderation.neutral.banned", {"name": name, "term": term})

    def banned_for(self, *, name: object, reason: object, term: object) -> Line:
        return Line(
            "moderation.neutral.banned_for",
            {
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def bot_lacks_right(self, *, right: object) -> Line:
        return Line("moderation.neutral.bot_lacks_right", {"right": right})

    def feature_disabled(self, *, feature: object) -> Line:
        return Line("moderation.neutral.feature_disabled", {"feature": feature})

    def kick_usage(self) -> Line:
        return Line("moderation.neutral.kick_usage", {})

    def kicked(self, *, name: object) -> Line:
        return Line("moderation.neutral.kicked", {"name": name})

    def kicked_for(self, *, name: object, reason: object) -> Line:
        return Line("moderation.neutral.kicked_for", {"name": name, "reason": reason})

    def log_ban_default(self, *, chat: object, moderator: object, term: object) -> Line:
        return Line(
            "moderation.neutral.log_ban_default",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_ban_expired(self, *, chat: object, id: object, name: object) -> Line:
        return Line(
            "moderation.neutral.log_ban_expired",
            {
                "chat": chat,
                "id": id,
                "name": name,
            },
        )

    def log_banned(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_banned",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_banned_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_banned_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def log_feature(
        self,
        *,
        chat: object,
        feature: object,
        moderator: object,
        state: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_feature",
            {
                "chat": chat,
                "feature": feature,
                "moderator": moderator,
                "state": state,
            },
        )

    def log_kicked(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_kicked",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_kicked_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_kicked_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
            },
        )

    def log_mute_default(
        self,
        *,
        chat: object,
        moderator: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_mute_default",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_mute_expired(self, *, chat: object, id: object, name: object) -> Line:
        return Line(
            "moderation.neutral.log_mute_expired",
            {
                "chat": chat,
                "id": id,
                "name": name,
            },
        )

    def log_muted(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_muted",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_muted_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_muted_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def log_unbanned(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_unbanned",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_unlinked(self, *, chat: object, moderator: object) -> Line:
        return Line(
            "moderation.neutral.log_unlinked",
            {
                "chat": chat,
                "moderator": moderator,
            },
        )

    def log_unmuted(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_unmuted",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_unwarned(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_unwarned",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_voice(self, *, chat: object, moderator: object) -> Line:
        return Line(
            "moderation.neutral.log_voice",
            {
                "chat": chat,
                "moderator": moderator,
            },
        )

    def log_warn_expired(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warn_expired",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "name": name,
            },
        )

    def log_warn_expiry(self, *, chat: object, moderator: object, term: object) -> Line:
        return Line(
            "moderation.neutral.log_warn_expiry",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_warn_limit(self, *, chat: object, limit: object, moderator: object) -> Line:
        return Line(
            "moderation.neutral.log_warn_limit",
            {
                "chat": chat,
                "limit": limit,
                "moderator": moderator,
            },
        )

    def log_warn_penalty(
        self,
        *,
        chat: object,
        moderator: object,
        penalty: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warn_penalty",
            {
                "chat": chat,
                "moderator": moderator,
                "penalty": penalty,
            },
        )

    def log_warn_penalty_banned(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warn_penalty_banned",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_warn_penalty_kicked(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warn_penalty_kicked",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_warn_penalty_muted(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warn_penalty_muted",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_warned(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warned",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_warned_for(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.neutral.log_warned_for",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "reason": reason,
            },
        )

    def moderator_lacks_right(self, *, right: object) -> Line:
        return Line("moderation.neutral.moderator_lacks_right", {"right": right})

    def mute_default_current(self, *, term: object) -> Line:
        return Line("moderation.neutral.mute_default_current", {"term": term})

    def mute_default_set(self, *, term: object) -> Line:
        return Line("moderation.neutral.mute_default_set", {"term": term})

    def mute_expired(self, *, name: object) -> Line:
        return Line("moderation.neutral.mute_expired", {"name": name})

    def mute_usage(self) -> Line:
        return Line("moderation.neutral.mute_usage", {})

    def muted(self, *, name: object, term: object) -> Line:
        return Line("moderation.neutral.muted", {"name": name, "term": term})

    def muted_for(self, *, name: object, reason: object, term: object) -> Line:
        return Line(
            "moderation.neutral.muted_for",
            {
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def no_reason(self) -> Line:
        return Line("moderation.neutral.no_reason", {})

    def no_warnings(self, *, name: object) -> Line:
        return Line("moderation.neutral.no_warnings", {"name": name})

    def not_banned(self, *, name: object) -> Line:
        return Line("moderation.neutral.not_banned", {"name": name})

    def not_muted(self, *, name: object) -> Line:
        return Line("moderation.neutral.not_muted", {"name": name})

    def owner_only(self) -> Line:
        return Line("moderation.neutral.owner_only", {})

    def target_absent(self, *, name: object) -> Line:
        return Line("moderation.neutral.target_absent", {"name": name})

    def target_is_admin(self, *, name: object) -> Line:
        return Line("moderation.neutral.target_is_admin", {"name": name})

    def term_out_of_range(self, *, max: object, min: object) -> Line:
        return Line("moderation.neutral.term_out_of_range", {"max": max, "min": min})

    def unban_usage(self) -> Line:
        return Line("moderation.neutral.unban_usage", {})

    def unbanned(self, *, name: object) -> Line:
        return Line("moderation.neutral.unbanned", {"name": name})

    def unmute_usage(self) -> Line:
        return Line("moderation.neutral.unmute_usage", {})

    def unmuted(self, *, name: object) -> Line:
        return Line("moderation.neutral.unmuted", {"name": name})

    def unwarn_usage(self) -> Line:
        return Line("moderation.neutral.unwarn_usage", {})

    def unwarned(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.neutral.unwarned",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def user_not_found(self, *, query: object) -> Line:
        return Line("moderation.neutral.user_not_found", {"query": query})

    def voice_current(self) -> Line:
        return Line("moderation.neutral.voice_current", {})

    def voice_set(self) -> Line:
        return Line("moderation.neutral.voice_set", {})

    def warn_expired(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.neutral.warn_expired",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def warn_expiry_current(self, *, term: object) -> Line:
        return Line("moderation.neutral.warn_expiry_current", {"term": term})

    def warn_expiry_set(self, *, term: object) -> Line:
        return Line("moderation.neutral.warn_expiry_set", {"term": term})

    def warn_limit_current(self, *, limit: object, max: object, min: object) -> Line:
        return Line(
            "moderation.neutral.warn_limit_current",
            {
                "limit": limit,
                "max": max,
                "min": min,
            },
        )

    def warn_limit_out_of_range(self, *, max: object, min: object) -> Line:
        return Line(
            "moderation.neutral.warn_limit_out_of_range",
            {
                "max": max,
                "min": min,
            },
        )

    def warn_limit_set(self, *, limit: object) -> Line:
        return Line("moderation.neutral.warn_limit_set", {"limit": limit})

    def warn_penalty_banned(self, *, limit: object, name: object, term: object) -> Line:
        return Line(
            "moderation.neutral.warn_penalty_banned",
            {
                "limit": limit,
                "name": name,
                "term": term,
            },
        )

    def warn_penalty_current(self, *, penalty: object) -> Line:
        return Line("moderation.neutral.warn_penalty_current", {"penalty": penalty})

    def warn_penalty_kicked(self, *, limit: object, name: object) -> Line:
        return Line(
            "moderation.neutral.warn_penalty_kicked",
            {
                "limit": limit,
                "name": name,
            },
        )

    def warn_penalty_muted(self, *, limit: object, name: object, term: object) -> Line:
        return Line(
            "moderation.neutral.warn_penalty_muted",
            {
                "limit": limit,
                "name": name,
                "term": term,
            },
        )

    def warn_penalty_set(self, *, penalty: object) -> Line:
        return Line("moderation.neutral.warn_penalty_set", {"penalty": penalty})

    def warn_usage(self) -> Line:
        return Line("moderation.neutral.warn_usage", {})

    def warned(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.neutral.warned",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def warned_for(
        self,
        *,
        count: object,
        limit: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.neutral.warned_for",
            {
                "count": count,
                "limit": limit,
                "name": name,
                "reason": reason,
            },
        )

    def warns_item(self, *, left: object, reason: object) -> Line:
        return Line("moderation.neutral.warns_item", {"left": left, "reason": reason})

    def warns_item_forever(self, *, reason: object) -> Line:
        return Line("moderation.neutral.warns_item_forever", {"reason": reason})

    def warns_list(
        self,
        *,
        count: object,
        items: object,
        limit: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.neutral.warns_list",
            {
                "count": count,
                "items": items,
                "limit": limit,
                "name": name,
            },
        )

    def warns_none(self, *, name: object) -> Line:
        return Line("moderation.neutral.warns_none", {"name": name})

    def warns_usage(self) -> Line:
        return Line("moderation.neutral.warns_usage", {})


class _ModerationPenaltyDialogs:
    def ban(self) -> Line:
        return Line("moderation.penalty.ban", {})

    def kick(self) -> Line:
        return Line("moderation.penalty.kick", {})

    def mute(self) -> Line:
        return Line("moderation.penalty.mute", {})

    def timed(self, *, penalty: object, term: object) -> Line:
        return Line("moderation.penalty.timed", {"penalty": penalty, "term": term})


class _ModerationRightDialogs:
    def change_info(self) -> Line:
        return Line("moderation.right.change_info", {})

    def restrict_members(self) -> Line:
        return Line("moderation.right.restrict_members", {})


class _ModerationRoughDialogs:
    def admin_chat_current(self, *, chat: object) -> Line:
        return Line("moderation.rough.admin_chat_current", {"chat": chat})

    def admin_chat_linked(self, *, chat: object) -> Line:
        return Line("moderation.rough.admin_chat_linked", {"chat": chat})

    def admin_chat_none(self) -> Line:
        return Line("moderation.rough.admin_chat_none", {})

    def admin_chat_not_found(self, *, query: object) -> Line:
        return Line("moderation.rough.admin_chat_not_found", {"query": query})

    def admin_chat_not_linked(self) -> Line:
        return Line("moderation.rough.admin_chat_not_linked", {})

    def admin_chat_requested(self, *, chat: object, command: object) -> Line:
        return Line(
            "moderation.rough.admin_chat_requested",
            {
                "chat": chat,
                "command": command,
            },
        )

    def admin_chat_self(self) -> Line:
        return Line("moderation.rough.admin_chat_self", {})

    def admin_chat_taken(self) -> Line:
        return Line("moderation.rough.admin_chat_taken", {})

    def admin_chat_unlinked(self, *, chat: object) -> Line:
        return Line("moderation.rough.admin_chat_unlinked", {"chat": chat})

    def anonymous(self) -> Line:
        return Line("moderation.rough.anonymous", {})

    def ban_default_current(self, *, term: object) -> Line:
        return Line("moderation.rough.ban_default_current", {"term": term})

    def ban_default_set(self, *, term: object) -> Line:
        return Line("moderation.rough.ban_default_set", {"term": term})

    def ban_usage(self) -> Line:
        return Line("moderation.rough.ban_usage", {})

    def banned(self, *, name: object, term: object) -> Line:
        return Line("moderation.rough.banned", {"name": name, "term": term})

    def banned_for(self, *, name: object, reason: object, term: object) -> Line:
        return Line(
            "moderation.rough.banned_for",
            {
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def bot_lacks_right(self, *, right: object) -> Line:
        return Line("moderation.rough.bot_lacks_right", {"right": right})

    def feature_disabled(self, *, feature: object) -> Line:
        return Line("moderation.rough.feature_disabled", {"feature": feature})

    def kick_usage(self) -> Line:
        return Line("moderation.rough.kick_usage", {})

    def kicked(self, *, name: object) -> Line:
        return Line("moderation.rough.kicked", {"name": name})

    def kicked_for(self, *, name: object, reason: object) -> Line:
        return Line("moderation.rough.kicked_for", {"name": name, "reason": reason})

    def log_ban_default(self, *, chat: object, moderator: object, term: object) -> Line:
        return Line(
            "moderation.rough.log_ban_default",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_ban_expired(self, *, chat: object, id: object, name: object) -> Line:
        return Line(
            "moderation.rough.log_ban_expired",
            {
                "chat": chat,
                "id": id,
                "name": name,
            },
        )

    def log_banned(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_banned",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_banned_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_banned_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def log_feature(
        self,
        *,
        chat: object,
        feature: object,
        moderator: object,
        state: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_feature",
            {
                "chat": chat,
                "feature": feature,
                "moderator": moderator,
                "state": state,
            },
        )

    def log_kicked(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_kicked",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_kicked_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_kicked_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
            },
        )

    def log_mute_default(
        self,
        *,
        chat: object,
        moderator: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_mute_default",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_mute_expired(self, *, chat: object, id: object, name: object) -> Line:
        return Line(
            "moderation.rough.log_mute_expired",
            {
                "chat": chat,
                "id": id,
                "name": name,
            },
        )

    def log_muted(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_muted",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_muted_for(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
        reason: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_muted_for",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def log_unbanned(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_unbanned",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_unlinked(self, *, chat: object, moderator: object) -> Line:
        return Line(
            "moderation.rough.log_unlinked",
            {
                "chat": chat,
                "moderator": moderator,
            },
        )

    def log_unmuted(
        self,
        *,
        chat: object,
        id: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_unmuted",
            {
                "chat": chat,
                "id": id,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_unwarned(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_unwarned",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_voice(self, *, chat: object, moderator: object) -> Line:
        return Line(
            "moderation.rough.log_voice",
            {
                "chat": chat,
                "moderator": moderator,
            },
        )

    def log_warn_expired(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warn_expired",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "name": name,
            },
        )

    def log_warn_expiry(self, *, chat: object, moderator: object, term: object) -> Line:
        return Line(
            "moderation.rough.log_warn_expiry",
            {
                "chat": chat,
                "moderator": moderator,
                "term": term,
            },
        )

    def log_warn_limit(self, *, chat: object, limit: object, moderator: object) -> Line:
        return Line(
            "moderation.rough.log_warn_limit",
            {
                "chat": chat,
                "limit": limit,
                "moderator": moderator,
            },
        )

    def log_warn_penalty(
        self,
        *,
        chat: object,
        moderator: object,
        penalty: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warn_penalty",
            {
                "chat": chat,
                "moderator": moderator,
                "penalty": penalty,
            },
        )

    def log_warn_penalty_banned(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warn_penalty_banned",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_warn_penalty_kicked(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warn_penalty_kicked",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_warn_penalty_muted(
        self,
        *,
        chat: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        term: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warn_penalty_muted",
            {
                "chat": chat,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "term": term,
            },
        )

    def log_warned(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warned",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
            },
        )

    def log_warned_for(
        self,
        *,
        chat: object,
        count: object,
        id: object,
        limit: object,
        moderator: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.rough.log_warned_for",
            {
                "chat": chat,
                "count": count,
                "id": id,
                "limit": limit,
                "moderator": moderator,
                "name": name,
                "reason": reason,
            },
        )

    def moderator_lacks_right(self, *, right: object) -> Line:
        return Line("moderation.rough.moderator_lacks_right", {"right": right})

    def mute_default_current(self, *, term: object) -> Line:
        return Line("moderation.rough.mute_default_current", {"term": term})

    def mute_default_set(self, *, term: object) -> Line:
        return Line("moderation.rough.mute_default_set", {"term": term})

    def mute_expired(self, *, name: object) -> Line:
        return Line("moderation.rough.mute_expired", {"name": name})

    def mute_usage(self) -> Line:
        return Line("moderation.rough.mute_usage", {})

    def muted(self, *, name: object, term: object) -> Line:
        return Line("moderation.rough.muted", {"name": name, "term": term})

    def muted_for(self, *, name: object, reason: object, term: object) -> Line:
        return Line(
            "moderation.rough.muted_for",
            {
                "name": name,
                "reason": reason,
                "term": term,
            },
        )

    def no_reason(self) -> Line:
        return Line("moderation.rough.no_reason", {})

    def no_warnings(self, *, name: object) -> Line:
        return Line("moderation.rough.no_warnings", {"name": name})

    def not_banned(self, *, name: object) -> Line:
        return Line("moderation.rough.not_banned", {"name": name})

    def not_muted(self, *, name: object) -> Line:
        return Line("moderation.rough.not_muted", {"name": name})

    def owner_only(self) -> Line:
        return Line("moderation.rough.owner_only", {})

    def target_absent(self, *, name: object) -> Line:
        return Line("moderation.rough.target_absent", {"name": name})

    def target_is_admin(self, *, name: object) -> Line:
        return Line("moderation.rough.target_is_admin", {"name": name})

    def term_out_of_range(self, *, max: object, min: object) -> Line:
        return Line("moderation.rough.term_out_of_range", {"max": max, "min": min})

    def unban_usage(self) -> Line:
        return Line("moderation.rough.unban_usage", {})

    def unbanned(self, *, name: object) -> Line:
        return Line("moderation.rough.unbanned", {"name": name})

    def unmute_usage(self) -> Line:
        return Line("moderation.rough.unmute_usage", {})

    def unmuted(self, *, name: object) -> Line:
        return Line("moderation.rough.unmuted", {"name": name})

    def unwarn_usage(self) -> Line:
        return Line("moderation.rough.unwarn_usage", {})

    def unwarned(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.rough.unwarned",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def user_not_found(self, *, query: object) -> Line:
        return Line("moderation.rough.user_not_found", {"query": query})

    def voice_current(self) -> Line:
        return Line("moderation.rough.voice_current", {})

    def voice_set(self) -> Line:
        return Line("moderation.rough.voice_set", {})

    def warn_expired(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.rough.warn_expired",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def warn_expiry_current(self, *, term: object) -> Line:
        return Line("moderation.rough.warn_expiry_current", {"term": term})

    def warn_expiry_set(self, *, term: object) -> Line:
        return Line("moderation.rough.warn_expiry_set", {"term": term})

    def warn_limit_current(self, *, limit: object, max: object, min: object) -> Line:
        return Line(
            "moderation.rough.warn_limit_current",
            {
                "limit": limit,
                "max": max,
                "min": min,
            },
        )

    def warn_limit_out_of_range(self, *, max: object, min: object) -> Line:
        return Line(
            "moderation.rough.warn_limit_out_of_range",
            {
                "max": max,
                "min": min,
            },
        )

    def warn_limit_set(self, *, limit: object) -> Line:
        return Line("moderation.rough.warn_limit_set", {"limit": limit})

    def warn_penalty_banned(self, *, limit: object, name: object, term: object) -> Line:
        return Line(
            "moderation.rough.warn_penalty_banned",
            {
                "limit": limit,
                "name": name,
                "term": term,
            },
        )

    def warn_penalty_current(self, *, penalty: object) -> Line:
        return Line("moderation.rough.warn_penalty_current", {"penalty": penalty})

    def warn_penalty_kicked(self, *, limit: object, name: object) -> Line:
        return Line(
            "moderation.rough.warn_penalty_kicked",
            {
                "limit": limit,
                "name": name,
            },
        )

    def warn_penalty_muted(self, *, limit: object, name: object, term: object) -> Line:
        return Line(
            "moderation.rough.warn_penalty_muted",
            {
                "limit": limit,
                "name": name,
                "term": term,
            },
        )

    def warn_penalty_set(self, *, penalty: object) -> Line:
        return Line("moderation.rough.warn_penalty_set", {"penalty": penalty})

    def warn_usage(self) -> Line:
        return Line("moderation.rough.warn_usage", {})

    def warned(self, *, count: object, limit: object, name: object) -> Line:
        return Line(
            "moderation.rough.warned",
            {
                "count": count,
                "limit": limit,
                "name": name,
            },
        )

    def warned_for(
        self,
        *,
        count: object,
        limit: object,
        name: object,
        reason: object,
    ) -> Line:
        return Line(
            "moderation.rough.warned_for",
            {
                "count": count,
                "limit": limit,
                "name": name,
                "reason": reason,
            },
        )

    def warns_item(self, *, left: object, reason: object) -> Line:
        return Line("moderation.rough.warns_item", {"left": left, "reason": reason})

    def warns_item_forever(self, *, reason: object) -> Line:
        return Line("moderation.rough.warns_item_forever", {"reason": reason})

    def warns_list(
        self,
        *,
        count: object,
        items: object,
        limit: object,
        name: object,
    ) -> Line:
        return Line(
            "moderation.rough.warns_list",
            {
                "count": count,
                "items": items,
                "limit": limit,
                "name": name,
            },
        )

    def warns_none(self, *, name: object) -> Line:
        return Line("moderation.rough.warns_none", {"name": name})

    def warns_usage(self) -> Line:
        return Line("moderation.rough.warns_usage", {})


class _ModerationTermDialogs:
    def after(self, *, duration: object) -> Line:
        return Line("moderation.term.after", {"duration": duration})

    def days(self, *, count: object) -> Line:
        return Line("moderation.term.days", {"count": count})

    def forever(self) -> Line:
        return Line("moderation.term.forever", {})

    def hours(self, *, count: object) -> Line:
        return Line("moderation.term.hours", {"count": count})

    def limited(self, *, duration: object) -> Line:
        return Line("moderation.term.limited", {"duration": duration})

    def minutes(self, *, count: object) -> Line:
        return Line("moderation.term.minutes", {"count": count})

    def never(self) -> Line:
        return Line("moderation.term.never", {})

    def seconds(self, *, count: object) -> Line:
        return Line("moderation.term.seconds", {"count": count})


class _ModerationDialogs:
    feature = _ModerationFeatureDialogs()
    menu = _ModerationMenuDialogs()
    neutral = _ModerationNeutralDialogs()
    penalty = _ModerationPenaltyDialogs()
    right = _ModerationRightDialogs()
    rough = _ModerationRoughDialogs()
    term = _ModerationTermDialogs()

    def bot_added(self) -> Line:
        return Line("moderation.bot_added", {})

    def goodbye_updated(self, *, text: object) -> Line:
        return Line("moderation.goodbye_updated", {"text": text})

    def rules_updated(self, *, rules: object) -> Line:
        return Line("moderation.rules_updated", {"rules": rules})

    def welcome_updated(self, *, text: object) -> Line:
        return Line("moderation.welcome_updated", {"text": text})


class _MusicShazamDialogs:
    def not_recognized(self) -> Line:
        return Line("music.shazam.not_recognized", {})

    def recognized(self, *, artist: object, title: object) -> Line:
        return Line("music.shazam.recognized", {"artist": artist, "title": title})

    def too_big(self) -> Line:
        return Line("music.shazam.too_big", {})

    def usage(self) -> Line:
        return Line("music.shazam.usage", {})


class _MusicDialogs:
    shazam = _MusicShazamDialogs()

    def button(self, *, author: object, duration: object, title: object) -> Line:
        return Line(
            "music.button",
            {
                "author": author,
                "duration": duration,
                "title": title,
            },
        )

    def downloading(self) -> Line:
        return Line("music.downloading", {})

    def failed(self) -> Line:
        return Line("music.failed", {})

    def not_found(self, *, query: object) -> Line:
        return Line("music.not_found", {"query": query})

    def results(self, *, query: object) -> Line:
        return Line("music.results", {"query": query})

    def usage(self) -> Line:
        return Line("music.usage", {})


class _NotInLanguageDialogs:
    def anime(self) -> Line:
        return Line("not_in_language.anime", {})

    def quote(self) -> Line:
        return Line("not_in_language.quote", {})

    def wordle(self) -> Line:
        return Line("not_in_language.wordle", {})


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


class _PromoRewardDialogs:
    def cheston(self, *, amount: object) -> Line:
        return Line("promo.reward.cheston", {"amount": amount})

    def cooldown_reset(self) -> Line:
        return Line("promo.reward.cooldown_reset", {})

    def full_hunger(self) -> Line:
        return Line("promo.reward.full_hunger", {})

    def heal(self) -> Line:
        return Line("promo.reward.heal", {})

    def hunger(self, *, percent: object) -> Line:
        return Line("promo.reward.hunger", {"percent": percent})

    def progress(self, *, percent: object) -> Line:
        return Line("promo.reward.progress", {"percent": percent})

    def rc(self, *, amount: object) -> Line:
        return Line("promo.reward.rc", {"amount": amount})

    def stat(self, *, amount: object, stat: object) -> Line:
        return Line("promo.reward.stat", {"amount": amount, "stat": stat})

    def stat_capped(self, *, amount: object, stat: object) -> Line:
        return Line("promo.reward.stat_capped", {"amount": amount, "stat": stat})


class _PromoDialogs:
    reward = _PromoRewardDialogs()

    def activated(self, *, name: object, rewards: object) -> Line:
        return Line("promo.activated", {"name": name, "rewards": rewards})

    def already(self, *, name: object) -> Line:
        return Line("promo.already", {"name": name})

    def exhausted(self, *, name: object) -> Line:
        return Line("promo.exhausted", {"name": name})

    def expired(self, *, name: object) -> Line:
        return Line("promo.expired", {"name": name})

    def not_found(self, *, name: object) -> Line:
        return Line("promo.not_found", {"name": name})

    def usage(self) -> Line:
        return Line("promo.usage", {})


class _QuizDialogs:
    def correct(
        self,
        *,
        award: object,
        minutes: object,
        multiplier: object,
        streak: object,
    ) -> Line:
        return Line(
            "quiz.correct",
            {
                "award": award,
                "minutes": minutes,
                "multiplier": multiplier,
                "streak": streak,
            },
        )

    def false_button(self) -> Line:
        return Line("quiz.false_button", {})

    def not_active(self) -> Line:
        return Line("quiz.not_active", {})

    def not_yours(self) -> Line:
        return Line("quiz.not_yours", {})

    def play_again(self) -> Line:
        return Line("quiz.play_again", {})

    def result(self, *, answer: object, choice: object, status: object) -> Line:
        return Line(
            "quiz.result",
            {
                "answer": answer,
                "choice": choice,
                "status": status,
            },
        )

    def streak_broken(self, *, streak: object) -> Line:
        return Line("quiz.streak_broken", {"streak": streak})

    def streak_expired(self, *, streak: object) -> Line:
        return Line("quiz.streak_expired", {"streak": streak})

    def true_button(self) -> Line:
        return Line("quiz.true_button", {})

    def true_false_title(self) -> Line:
        return Line("quiz.true_false_title", {})

    def whois_title(self) -> Line:
        return Line("quiz.whois_title", {})

    def wrong(self) -> Line:
        return Line("quiz.wrong", {})

    def wrong_streak(self, *, streak: object) -> Line:
        return Line("quiz.wrong_streak", {"streak": streak})


class _RichDialogs:
    def download_failed(self) -> Line:
        return Line("rich.download_failed", {})

    def empty(self) -> Line:
        return Line("rich.empty", {})

    def not_utf8(self) -> Line:
        return Line("rich.not_utf8", {})

    def rejected(self, *, error: object) -> Line:
        return Line("rich.rejected", {"error": error})

    def too_long(self, *, limit: object) -> Line:
        return Line("rich.too_long", {"limit": limit})

    def usage(self) -> Line:
        return Line("rich.usage", {})


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


class _SubscriptionDialogs:
    def check_button(self) -> Line:
        return Line("subscription.check_button", {})

    def confirmed(self) -> Line:
        return Line("subscription.confirmed", {})

    def not_yet(self) -> Line:
        return Line("subscription.not_yet", {})

    def required(self, *, channel: object) -> Line:
        return Line("subscription.required", {"channel": channel})

    def required_alert(self, *, channel: object) -> Line:
        return Line("subscription.required_alert", {"channel": channel})

    def subscribe_button(self) -> Line:
        return Line("subscription.subscribe_button", {})


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

    def power_title(self, *, count: object) -> Line:
        return Line("tops.power_title", {"count": count})

    def power_value(self, *, power: object, rank: object) -> Line:
        return Line("tops.power_value", {"power": power, "rank": rank})

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

    def bot(self) -> Line:
        return Line("transfer.errors.bot", {})

    def failed(self) -> Line:
        return Line("transfer.errors.failed", {})

    def insufficient_balance(self) -> Line:
        return Line("transfer.errors.insufficient_balance", {})

    def not_a_person(self) -> Line:
        return Line("transfer.errors.not_a_person", {})

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

    def spouse(self) -> Line:
        return Line("transfer.errors.spouse", {})


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


class _VocabColorDialogs:
    def blue(self) -> Line:
        return Line("vocab.color.blue", {})

    def green(self) -> Line:
        return Line("vocab.color.green", {})

    def red(self) -> Line:
        return Line("vocab.color.red", {})

    def white(self) -> Line:
        return Line("vocab.color.white", {})

    def yellow(self) -> Line:
        return Line("vocab.color.yellow", {})


class _VocabHungerDialogs:
    def deadly(self) -> Line:
        return Line("vocab.hunger.deadly", {})

    def full(self) -> Line:
        return Line("vocab.hunger.full", {})

    def light(self) -> Line:
        return Line("vocab.hunger.light", {})

    def strong(self) -> Line:
        return Line("vocab.hunger.strong", {})


class _VocabKaguneDialogs:
    def bikaku(self) -> Line:
        return Line("vocab.kagune.bikaku", {})

    def koukaku(self) -> Line:
        return Line("vocab.kagune.koukaku", {})

    def rinkaku(self) -> Line:
        return Line("vocab.kagune.rinkaku", {})

    def ukaku(self) -> Line:
        return Line("vocab.kagune.ukaku", {})


class _VocabRaceDialogs:
    def ccg(self) -> Line:
        return Line("vocab.race.ccg", {})

    def ghoul(self) -> Line:
        return Line("vocab.race.ghoul", {})

    def human(self) -> Line:
        return Line("vocab.race.human", {})


class _VocabStatDialogs:
    def dexterity(self) -> Line:
        return Line("vocab.stat.dexterity", {})

    def health(self) -> Line:
        return Line("vocab.stat.health", {})

    def max_health(self) -> Line:
        return Line("vocab.stat.max_health", {})

    def regeneration(self) -> Line:
        return Line("vocab.stat.regeneration", {})

    def speed(self) -> Line:
        return Line("vocab.stat.speed", {})

    def strength(self) -> Line:
        return Line("vocab.stat.strength", {})


class _VocabTimeDialogs:
    def days(self, *, count: object) -> Line:
        return Line("vocab.time.days", {"count": count})

    def hours(self, *, count: object) -> Line:
        return Line("vocab.time.hours", {"count": count})

    def minutes(self, *, count: object) -> Line:
        return Line("vocab.time.minutes", {"count": count})

    def months(self, *, count: object) -> Line:
        return Line("vocab.time.months", {"count": count})


class _VocabDialogs:
    color = _VocabColorDialogs()
    hunger = _VocabHungerDialogs()
    kagune = _VocabKaguneDialogs()
    race = _VocabRaceDialogs()
    stat = _VocabStatDialogs()
    time = _VocabTimeDialogs()

    def mob(self) -> Line:
        return Line("vocab.mob", {})


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
    divorce = _DivorceDialogs()
    duel = _DuelDialogs()
    eat_human = _EatHumanDialogs()
    errors = _ErrorsDialogs()
    family = _FamilyDialogs()
    fight = _FightDialogs()
    fun = _FunDialogs()
    ghoul = _GhoulDialogs()
    help = _HelpDialogs()
    kagune = _KaguneDialogs()
    link_media = _LinkMediaDialogs()
    lottery = _LotteryDialogs()
    marriage = _MarriageDialogs()
    mob = _MobDialogs()
    moderation = _ModerationDialogs()
    music = _MusicDialogs()
    not_in_language = _NotInLanguageDialogs()
    notify = _NotifyDialogs()
    profile = _ProfileDialogs()
    promo = _PromoDialogs()
    quiz = _QuizDialogs()
    rich = _RichDialogs()
    roast = _RoastDialogs()
    rp = _RpDialogs()
    rules = _RulesDialogs()
    snap = _SnapDialogs()
    stats = _StatsDialogs()
    status = _StatusDialogs()
    subscription = _SubscriptionDialogs()
    tops = _TopsDialogs()
    transfer = _TransferDialogs()
    vocab = _VocabDialogs()
    wordle = _WordleDialogs()

    def balance(self, *, balance: object, name: object) -> Line:
        return Line("balance", {"balance": balance, "name": name})

    def bot(self) -> Line:
        return Line("bot", {})

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
    "admin.promo.bad_line": frozenset({"line"}),
    "admin.promo.card.activations": frozenset(),
    "admin.promo.card.activations_value": frozenset({"limit", "used"}),
    "admin.promo.card.back_button": frozenset(),
    "admin.promo.card.cancel_button": frozenset(),
    "admin.promo.card.column_field": frozenset(),
    "admin.promo.card.column_value": frozenset(),
    "admin.promo.card.confirm_button": frozenset(),
    "admin.promo.card.confirm_question": frozenset(),
    "admin.promo.card.created": frozenset(),
    "admin.promo.card.delete_button": frozenset(),
    "admin.promo.card.deleted": frozenset(),
    "admin.promo.card.expired_at": frozenset({"date"}),
    "admin.promo.card.gone": frozenset(),
    "admin.promo.card.not_found": frozenset({"name"}),
    "admin.promo.card.rewards": frozenset(),
    "admin.promo.card.status": frozenset(),
    "admin.promo.card.term": frozenset(),
    "admin.promo.card.title": frozenset({"name"}),
    "admin.promo.card.until": frozenset({"date", "left"}),
    "admin.promo.card.usage": frozenset(),
    "admin.promo.card.who_when": frozenset({"date", "who"}),
    "admin.promo.catalog.column_activations": frozenset(),
    "admin.promo.catalog.column_name": frozenset(),
    "admin.promo.catalog.column_status": frozenset(),
    "admin.promo.catalog.column_term": frozenset(),
    "admin.promo.catalog.empty": frozenset(),
    "admin.promo.catalog.term_until": frozenset({"date"}),
    "admin.promo.catalog.title": frozenset(),
    "admin.promo.created": frozenset({"activations", "name", "rewards", "until"}),
    "admin.promo.forever": frozenset(),
    "admin.promo.name_taken": frozenset({"name"}),
    "admin.promo.status.active": frozenset(),
    "admin.promo.status.deleted": frozenset(),
    "admin.promo.status.exhausted": frozenset(),
    "admin.promo.status.expired": frozenset(),
    "admin.promo.until": frozenset({"date"}),
    "admin.promo.usage": frozenset(),
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
    "admin.service.marked": frozenset({"id"}),
    "admin.service.unmark_usage": frozenset(),
    "admin.service.unmarked": frozenset({"id"}),
    "admin.service.usage": frozenset(),
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
    "combat_power.rich.column_hunger": frozenset(),
    "combat_power.rich.column_kagune": frozenset(),
    "combat_power.rich.column_stat": frozenset(),
    "combat_power.rich.column_value": frozenset(),
    "combat_power.rich.combat_note": frozenset(),
    "combat_power.rich.hints": frozenset(),
    "combat_power.rich.kagune_row": frozenset(),
    "combat_power.rich.title": frozenset({"danger_rank", "name"}),
    "combat_power.rich.total_row": frozenset(),
    "combat_power.short": frozenset({"effective_power", "vacuum_power"}),
    "divorce.ask": frozenset(),
    "divorce.button": frozenset(),
    "divorce.dissolved": frozenset({"amount", "heir", "name"}),
    "divorce.done": frozenset({"name"}),
    "divorce.not_married": frozenset(),
    "divorce.stale": frozenset(),
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
    "duel.refusals.spouses": frozenset(),
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
    "errors.not_enough_rc": frozenset({"rc"}),
    "errors.quiz.busy": frozenset({"seconds"}),
    "errors.quiz.email_missing": frozenset(),
    "errors.quiz.session_missing": frozenset({"email"}),
    "errors.unexpected": frozenset({"error"}),
    "errors.user_not_found": frozenset({"query"}),
    "errors.username_not_found": frozenset({"username"}),
    "family.list.empty": frozenset(),
    "family.list.message": frozenset({"count", "rows"}),
    "family.list.more": frozenset({"count"}),
    "family.list.named_row": frozenset({"age", "members", "name", "place", "since"}),
    "family.list.row": frozenset({"age", "members", "place", "since"}),
    "family.rename.ask": frozenset({"name", "proposer", "rows"}),
    "family.rename.buttons.agree": frozenset(),
    "family.rename.buttons.decline": frozenset(),
    "family.rename.buttons.private": frozenset(),
    "family.rename.consent.accepted": frozenset(),
    "family.rename.consent.declined": frozenset(),
    "family.rename.consent.renamed": frozenset(),
    "family.rename.declined": frozenset({"name", "person"}),
    "family.rename.declined_private": frozenset(),
    "family.rename.expired": frozenset({"name"}),
    "family.rename.link_not_family": frozenset(),
    "family.rename.link_stale": frozenset(),
    "family.rename.refusals.already_pending": frozenset(),
    "family.rename.refusals.bad_name": frozenset({"limit"}),
    "family.rename.refusals.not_married": frozenset(),
    "family.rename.renamed": frozenset({"name"}),
    "family.rename.usage": frozenset(),
    "family.rename.vote": frozenset({"name"}),
    "family.rename.voted": frozenset(),
    "family.row": frozenset({"age", "name", "since"}),
    "family.single": frozenset(),
    "family.title": frozenset(),
    "family.title_named": frozenset({"name"}),
    "family.top_name": frozenset({"members"}),
    "family.view": frozenset({"balance", "rows", "title"}),
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
    "fun.edits.empty": frozenset(),
    "fun.nobody": frozenset(),
    "fun.number": frozenset({"number"}),
    "fun.pick.result": frozenset({"choice"}),
    "fun.pick.too_few": frozenset(),
    "fun.pick.too_long": frozenset(),
    "fun.pick.too_many": frozenset({"max_items"}),
    "fun.quote.not_found": frozenset(),
    "fun.random_participant": frozenset({"mention"}),
    "fun.search.cooldown": frozenset({"seconds"}),
    "fun.search.failed": frozenset(),
    "fun.search.limit_reached": frozenset(),
    "fun.search.unavailable": frozenset(),
    "fun.search.usage": frozenset(),
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
    "ghoul.rich_profile.coffee": frozenset({"count"}),
    "ghoul.rich_profile.deaths": frozenset({"count"}),
    "ghoul.rich_profile.fights": frozenset({"losses", "total", "wins"}),
    "ghoul.rich_profile.ghouls": frozenset({"count"}),
    "ghoul.rich_profile.health": frozenset({"health", "max_health"}),
    "ghoul.rich_profile.humans": frozenset({"count"}),
    "ghoul.rich_profile.hunger": frozenset({"hunger", "tier"}),
    "ghoul.rich_profile.kagune_row": frozenset({"kagune", "strength"}),
    "ghoul.rich_profile.kagune_types": frozenset(),
    "ghoul.rich_profile.kakuja": frozenset({"status"}),
    "ghoul.rich_profile.kakuja_no": frozenset(),
    "ghoul.rich_profile.kakuja_yes": frozenset(),
    "ghoul.rich_profile.level": frozenset({"level"}),
    "ghoul.rich_profile.mob_fights": frozenset({"losses", "total", "wins"}),
    "ghoul.rich_profile.power": frozenset({"power"}),
    "ghoul.rich_profile.rc": frozenset({"rc"}),
    "ghoul.rich_profile.snaps": frozenset({"count"}),
    "ghoul.rich_profile.stat_row": frozenset({"stat", "value"}),
    "ghoul.rich_profile.stats": frozenset(),
    "ghoul.rich_profile.title": frozenset({"danger_rank", "name"}),
    "help.did_you_mean": frozenset({"query"}),
    "help.more": frozenset(),
    "help.not_found": frozenset({"query"}),
    "help.sections": frozenset({"rows"}),
    "kagune.evolution.all_kagune_done": frozenset(),
    "kagune.evolution.already_kakuja": frozenset(),
    "kagune.evolution.buy_kagune_button": frozenset({"cheston", "kagune", "rc"}),
    "kagune.evolution.buy_kakuja_button": frozenset({"cheston", "rc"}),
    "kagune.evolution.column_status": frozenset(),
    "kagune.evolution.column_type": frozenset(),
    "kagune.evolution.kagune_done": frozenset({"cheston", "kagune", "rc", "strength"}),
    "kagune.evolution.kakuja_done": frozenset({"cheston", "rc"}),
    "kagune.evolution.kakuja_no": frozenset(),
    "kagune.evolution.kakuja_row": frozenset(),
    "kagune.evolution.kakuja_yes": frozenset(),
    "kagune.evolution.not_owned": frozenset(),
    "kagune.evolution.owned": frozenset({"strength"}),
    "kagune.evolution.title": frozenset(),
    "kagune.evolution.warning": frozenset(),
    "kagune.guide.column_type": frozenset(),
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
    "link_media.too_large": frozenset(),
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
    "marriage.ask": frozenset({"price", "proposer", "target"}),
    "marriage.buttons.decline": frozenset(),
    "marriage.buttons.family": frozenset(),
    "marriage.buttons.family_decline": frozenset(),
    "marriage.buttons.family_vote": frozenset(),
    "marriage.buttons.pay": frozenset({"price"}),
    "marriage.buttons.proposer": frozenset(),
    "marriage.buttons.target": frozenset(),
    "marriage.consent.accepted": frozenset(),
    "marriage.consent.already": frozenset(),
    "marriage.consent.declined": frozenset(),
    "marriage.consent.married": frozenset(),
    "marriage.consent.not_enough_money": frozenset({"price"}),
    "marriage.consent.not_invited": frozenset(),
    "marriage.consent.stale": frozenset(),
    "marriage.declined": frozenset({"name", "price", "proposer"}),
    "marriage.expired": frozenset({"price", "proposer"}),
    "marriage.failed.family_changed": frozenset({"proposer"}),
    "marriage.failed.target_broke": frozenset({"price", "target"}),
    "marriage.failed.target_taken": frozenset({"target"}),
    "marriage.family_declined": frozenset(),
    "marriage.family_hint": frozenset({"proposer"}),
    "marriage.family_vote": frozenset({"proposer", "target"}),
    "marriage.family_voted": frozenset(),
    "marriage.invite": frozenset({"proposer", "rows", "target"}),
    "marriage.link_not_family": frozenset(),
    "marriage.link_stale": frozenset(),
    "marriage.married": frozenset({"members", "target"}),
    "marriage.not_your_button": frozenset(),
    "marriage.refusals.already_proposed": frozenset(),
    "marriage.refusals.bot": frozenset(),
    "marriage.refusals.not_a_person": frozenset(),
    "marriage.refusals.not_enough_money": frozenset({"price"}),
    "marriage.refusals.not_registered": frozenset(),
    "marriage.refusals.same_family": frozenset(),
    "marriage.refusals.self": frozenset(),
    "marriage.refusals.target_married": frozenset(),
    "marriage.row_confirmed": frozenset({"name"}),
    "marriage.row_waiting": frozenset({"name"}),
    "marriage.usage": frozenset(),
    "marriage.user_not_found": frozenset({"target"}),
    "mob.busy": frozenset(),
    "mob.cooldown": frozenset({"minutes", "seconds"}),
    "mob.draw": frozenset(),
    "mob.lost": frozenset(),
    "mob.rc_found": frozenset({"rc"}),
    "mob.rewards": frozenset({"cheston", "progress"}),
    "mob.summary": frozenset({"losses", "outcome", "total", "wins"}),
    "moderation.bot_added": frozenset(),
    "moderation.feature.ban": frozenset(),
    "moderation.feature.kick": frozenset(),
    "moderation.feature.mute": frozenset(),
    "moderation.feature.notices": frozenset(),
    "moderation.feature.warns": frozenset(),
    "moderation.goodbye_updated": frozenset({"text"}),
    "moderation.menu.admin_chat": frozenset(),
    "moderation.menu.admin_chat_none": frozenset(),
    "moderation.menu.ban": frozenset(),
    "moderation.menu.ban_default": frozenset(),
    "moderation.menu.button_minus": frozenset(),
    "moderation.menu.button_next": frozenset(),
    "moderation.menu.button_off": frozenset({"name"}),
    "moderation.menu.button_on": frozenset({"name"}),
    "moderation.menu.button_plus": frozenset(),
    "moderation.menu.button_prev": frozenset(),
    "moderation.menu.button_value": frozenset({"name", "value"}),
    "moderation.menu.column_setting": frozenset(),
    "moderation.menu.column_value": frozenset(),
    "moderation.menu.hint": frozenset(),
    "moderation.menu.kick": frozenset(),
    "moderation.menu.mute": frozenset(),
    "moderation.menu.mute_default": frozenset(),
    "moderation.menu.no_right": frozenset({"right"}),
    "moderation.menu.not_admin": frozenset(),
    "moderation.menu.notices": frozenset(),
    "moderation.menu.off": frozenset(),
    "moderation.menu.on": frozenset(),
    "moderation.menu.title": frozenset({"chat"}),
    "moderation.menu.use_arrows": frozenset(),
    "moderation.menu.voice": frozenset(),
    "moderation.menu.voice_neutral": frozenset(),
    "moderation.menu.voice_rough": frozenset(),
    "moderation.menu.warn_expiry": frozenset(),
    "moderation.menu.warn_limit": frozenset(),
    "moderation.menu.warn_penalty": frozenset(),
    "moderation.menu.warns": frozenset(),
    "moderation.neutral.admin_chat_current": frozenset({"chat"}),
    "moderation.neutral.admin_chat_linked": frozenset({"chat"}),
    "moderation.neutral.admin_chat_none": frozenset(),
    "moderation.neutral.admin_chat_not_found": frozenset({"query"}),
    "moderation.neutral.admin_chat_not_linked": frozenset(),
    "moderation.neutral.admin_chat_requested": frozenset({"chat", "command"}),
    "moderation.neutral.admin_chat_self": frozenset(),
    "moderation.neutral.admin_chat_taken": frozenset(),
    "moderation.neutral.admin_chat_unlinked": frozenset({"chat"}),
    "moderation.neutral.anonymous": frozenset(),
    "moderation.neutral.ban_default_current": frozenset({"term"}),
    "moderation.neutral.ban_default_set": frozenset({"term"}),
    "moderation.neutral.ban_usage": frozenset(),
    "moderation.neutral.banned": frozenset({"name", "term"}),
    "moderation.neutral.banned_for": frozenset({"name", "reason", "term"}),
    "moderation.neutral.bot_lacks_right": frozenset({"right"}),
    "moderation.neutral.feature_disabled": frozenset({"feature"}),
    "moderation.neutral.kick_usage": frozenset(),
    "moderation.neutral.kicked": frozenset({"name"}),
    "moderation.neutral.kicked_for": frozenset({"name", "reason"}),
    "moderation.neutral.log_ban_default": frozenset({"chat", "moderator", "term"}),
    "moderation.neutral.log_ban_expired": frozenset({"chat", "id", "name"}),
    "moderation.neutral.log_banned": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.neutral.log_banned_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
            "term",
        }
    ),
    "moderation.neutral.log_feature": frozenset(
        {
            "chat",
            "feature",
            "moderator",
            "state",
        }
    ),
    "moderation.neutral.log_kicked": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.neutral.log_kicked_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
        }
    ),
    "moderation.neutral.log_mute_default": frozenset({"chat", "moderator", "term"}),
    "moderation.neutral.log_mute_expired": frozenset({"chat", "id", "name"}),
    "moderation.neutral.log_muted": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.neutral.log_muted_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
            "term",
        }
    ),
    "moderation.neutral.log_unbanned": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.neutral.log_unlinked": frozenset({"chat", "moderator"}),
    "moderation.neutral.log_unmuted": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.neutral.log_unwarned": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.neutral.log_voice": frozenset({"chat", "moderator"}),
    "moderation.neutral.log_warn_expired": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "name",
        }
    ),
    "moderation.neutral.log_warn_expiry": frozenset({"chat", "moderator", "term"}),
    "moderation.neutral.log_warn_limit": frozenset({"chat", "limit", "moderator"}),
    "moderation.neutral.log_warn_penalty": frozenset({"chat", "moderator", "penalty"}),
    "moderation.neutral.log_warn_penalty_banned": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.neutral.log_warn_penalty_kicked": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.neutral.log_warn_penalty_muted": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.neutral.log_warned": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.neutral.log_warned_for": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
            "reason",
        }
    ),
    "moderation.neutral.moderator_lacks_right": frozenset({"right"}),
    "moderation.neutral.mute_default_current": frozenset({"term"}),
    "moderation.neutral.mute_default_set": frozenset({"term"}),
    "moderation.neutral.mute_expired": frozenset({"name"}),
    "moderation.neutral.mute_usage": frozenset(),
    "moderation.neutral.muted": frozenset({"name", "term"}),
    "moderation.neutral.muted_for": frozenset({"name", "reason", "term"}),
    "moderation.neutral.no_reason": frozenset(),
    "moderation.neutral.no_warnings": frozenset({"name"}),
    "moderation.neutral.not_banned": frozenset({"name"}),
    "moderation.neutral.not_muted": frozenset({"name"}),
    "moderation.neutral.owner_only": frozenset(),
    "moderation.neutral.target_absent": frozenset({"name"}),
    "moderation.neutral.target_is_admin": frozenset({"name"}),
    "moderation.neutral.term_out_of_range": frozenset({"max", "min"}),
    "moderation.neutral.unban_usage": frozenset(),
    "moderation.neutral.unbanned": frozenset({"name"}),
    "moderation.neutral.unmute_usage": frozenset(),
    "moderation.neutral.unmuted": frozenset({"name"}),
    "moderation.neutral.unwarn_usage": frozenset(),
    "moderation.neutral.unwarned": frozenset({"count", "limit", "name"}),
    "moderation.neutral.user_not_found": frozenset({"query"}),
    "moderation.neutral.voice_current": frozenset(),
    "moderation.neutral.voice_set": frozenset(),
    "moderation.neutral.warn_expired": frozenset({"count", "limit", "name"}),
    "moderation.neutral.warn_expiry_current": frozenset({"term"}),
    "moderation.neutral.warn_expiry_set": frozenset({"term"}),
    "moderation.neutral.warn_limit_current": frozenset({"limit", "max", "min"}),
    "moderation.neutral.warn_limit_out_of_range": frozenset({"max", "min"}),
    "moderation.neutral.warn_limit_set": frozenset({"limit"}),
    "moderation.neutral.warn_penalty_banned": frozenset({"limit", "name", "term"}),
    "moderation.neutral.warn_penalty_current": frozenset({"penalty"}),
    "moderation.neutral.warn_penalty_kicked": frozenset({"limit", "name"}),
    "moderation.neutral.warn_penalty_muted": frozenset({"limit", "name", "term"}),
    "moderation.neutral.warn_penalty_set": frozenset({"penalty"}),
    "moderation.neutral.warn_usage": frozenset(),
    "moderation.neutral.warned": frozenset({"count", "limit", "name"}),
    "moderation.neutral.warned_for": frozenset({"count", "limit", "name", "reason"}),
    "moderation.neutral.warns_item": frozenset({"left", "reason"}),
    "moderation.neutral.warns_item_forever": frozenset({"reason"}),
    "moderation.neutral.warns_list": frozenset({"count", "items", "limit", "name"}),
    "moderation.neutral.warns_none": frozenset({"name"}),
    "moderation.neutral.warns_usage": frozenset(),
    "moderation.penalty.ban": frozenset(),
    "moderation.penalty.kick": frozenset(),
    "moderation.penalty.mute": frozenset(),
    "moderation.penalty.timed": frozenset({"penalty", "term"}),
    "moderation.right.change_info": frozenset(),
    "moderation.right.restrict_members": frozenset(),
    "moderation.rough.admin_chat_current": frozenset({"chat"}),
    "moderation.rough.admin_chat_linked": frozenset({"chat"}),
    "moderation.rough.admin_chat_none": frozenset(),
    "moderation.rough.admin_chat_not_found": frozenset({"query"}),
    "moderation.rough.admin_chat_not_linked": frozenset(),
    "moderation.rough.admin_chat_requested": frozenset({"chat", "command"}),
    "moderation.rough.admin_chat_self": frozenset(),
    "moderation.rough.admin_chat_taken": frozenset(),
    "moderation.rough.admin_chat_unlinked": frozenset({"chat"}),
    "moderation.rough.anonymous": frozenset(),
    "moderation.rough.ban_default_current": frozenset({"term"}),
    "moderation.rough.ban_default_set": frozenset({"term"}),
    "moderation.rough.ban_usage": frozenset(),
    "moderation.rough.banned": frozenset({"name", "term"}),
    "moderation.rough.banned_for": frozenset({"name", "reason", "term"}),
    "moderation.rough.bot_lacks_right": frozenset({"right"}),
    "moderation.rough.feature_disabled": frozenset({"feature"}),
    "moderation.rough.kick_usage": frozenset(),
    "moderation.rough.kicked": frozenset({"name"}),
    "moderation.rough.kicked_for": frozenset({"name", "reason"}),
    "moderation.rough.log_ban_default": frozenset({"chat", "moderator", "term"}),
    "moderation.rough.log_ban_expired": frozenset({"chat", "id", "name"}),
    "moderation.rough.log_banned": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.rough.log_banned_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
            "term",
        }
    ),
    "moderation.rough.log_feature": frozenset(
        {
            "chat",
            "feature",
            "moderator",
            "state",
        }
    ),
    "moderation.rough.log_kicked": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.rough.log_kicked_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
        }
    ),
    "moderation.rough.log_mute_default": frozenset({"chat", "moderator", "term"}),
    "moderation.rough.log_mute_expired": frozenset({"chat", "id", "name"}),
    "moderation.rough.log_muted": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.rough.log_muted_for": frozenset(
        {
            "chat",
            "id",
            "moderator",
            "name",
            "reason",
            "term",
        }
    ),
    "moderation.rough.log_unbanned": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.rough.log_unlinked": frozenset({"chat", "moderator"}),
    "moderation.rough.log_unmuted": frozenset({"chat", "id", "moderator", "name"}),
    "moderation.rough.log_unwarned": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.rough.log_voice": frozenset({"chat", "moderator"}),
    "moderation.rough.log_warn_expired": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "name",
        }
    ),
    "moderation.rough.log_warn_expiry": frozenset({"chat", "moderator", "term"}),
    "moderation.rough.log_warn_limit": frozenset({"chat", "limit", "moderator"}),
    "moderation.rough.log_warn_penalty": frozenset({"chat", "moderator", "penalty"}),
    "moderation.rough.log_warn_penalty_banned": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.rough.log_warn_penalty_kicked": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.rough.log_warn_penalty_muted": frozenset(
        {
            "chat",
            "id",
            "limit",
            "moderator",
            "name",
            "term",
        }
    ),
    "moderation.rough.log_warned": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
        }
    ),
    "moderation.rough.log_warned_for": frozenset(
        {
            "chat",
            "count",
            "id",
            "limit",
            "moderator",
            "name",
            "reason",
        }
    ),
    "moderation.rough.moderator_lacks_right": frozenset({"right"}),
    "moderation.rough.mute_default_current": frozenset({"term"}),
    "moderation.rough.mute_default_set": frozenset({"term"}),
    "moderation.rough.mute_expired": frozenset({"name"}),
    "moderation.rough.mute_usage": frozenset(),
    "moderation.rough.muted": frozenset({"name", "term"}),
    "moderation.rough.muted_for": frozenset({"name", "reason", "term"}),
    "moderation.rough.no_reason": frozenset(),
    "moderation.rough.no_warnings": frozenset({"name"}),
    "moderation.rough.not_banned": frozenset({"name"}),
    "moderation.rough.not_muted": frozenset({"name"}),
    "moderation.rough.owner_only": frozenset(),
    "moderation.rough.target_absent": frozenset({"name"}),
    "moderation.rough.target_is_admin": frozenset({"name"}),
    "moderation.rough.term_out_of_range": frozenset({"max", "min"}),
    "moderation.rough.unban_usage": frozenset(),
    "moderation.rough.unbanned": frozenset({"name"}),
    "moderation.rough.unmute_usage": frozenset(),
    "moderation.rough.unmuted": frozenset({"name"}),
    "moderation.rough.unwarn_usage": frozenset(),
    "moderation.rough.unwarned": frozenset({"count", "limit", "name"}),
    "moderation.rough.user_not_found": frozenset({"query"}),
    "moderation.rough.voice_current": frozenset(),
    "moderation.rough.voice_set": frozenset(),
    "moderation.rough.warn_expired": frozenset({"count", "limit", "name"}),
    "moderation.rough.warn_expiry_current": frozenset({"term"}),
    "moderation.rough.warn_expiry_set": frozenset({"term"}),
    "moderation.rough.warn_limit_current": frozenset({"limit", "max", "min"}),
    "moderation.rough.warn_limit_out_of_range": frozenset({"max", "min"}),
    "moderation.rough.warn_limit_set": frozenset({"limit"}),
    "moderation.rough.warn_penalty_banned": frozenset({"limit", "name", "term"}),
    "moderation.rough.warn_penalty_current": frozenset({"penalty"}),
    "moderation.rough.warn_penalty_kicked": frozenset({"limit", "name"}),
    "moderation.rough.warn_penalty_muted": frozenset({"limit", "name", "term"}),
    "moderation.rough.warn_penalty_set": frozenset({"penalty"}),
    "moderation.rough.warn_usage": frozenset(),
    "moderation.rough.warned": frozenset({"count", "limit", "name"}),
    "moderation.rough.warned_for": frozenset({"count", "limit", "name", "reason"}),
    "moderation.rough.warns_item": frozenset({"left", "reason"}),
    "moderation.rough.warns_item_forever": frozenset({"reason"}),
    "moderation.rough.warns_list": frozenset({"count", "items", "limit", "name"}),
    "moderation.rough.warns_none": frozenset({"name"}),
    "moderation.rough.warns_usage": frozenset(),
    "moderation.rules_updated": frozenset({"rules"}),
    "moderation.term.after": frozenset({"duration"}),
    "moderation.term.days": frozenset({"count"}),
    "moderation.term.forever": frozenset(),
    "moderation.term.hours": frozenset({"count"}),
    "moderation.term.limited": frozenset({"duration"}),
    "moderation.term.minutes": frozenset({"count"}),
    "moderation.term.never": frozenset(),
    "moderation.term.seconds": frozenset({"count"}),
    "moderation.welcome_updated": frozenset({"text"}),
    "music.button": frozenset({"author", "duration", "title"}),
    "music.downloading": frozenset(),
    "music.failed": frozenset(),
    "music.not_found": frozenset({"query"}),
    "music.results": frozenset({"query"}),
    "music.shazam.not_recognized": frozenset(),
    "music.shazam.recognized": frozenset({"artist", "title"}),
    "music.shazam.too_big": frozenset(),
    "music.shazam.usage": frozenset(),
    "music.usage": frozenset(),
    "not_in_language.anime": frozenset(),
    "not_in_language.quote": frozenset(),
    "not_in_language.wordle": frozenset(),
    "notify.death": frozenset({"cause", "level", "lifetime_rc_earned"}),
    "notify.death_cause.admin": frozenset(),
    "notify.death_cause.eaten": frozenset(),
    "notify.death_cause.starvation": frozenset(),
    "notify.health_full": frozenset(),
    "notify.hunger": frozenset({"threshold"}),
    "notify.level_up": frozenset({"cheston", "level", "rc", "stat_changes"}),
    "profile.card": frozenset({"balance", "name", "race"}),
    "profile.unknown_race": frozenset(),
    "promo.activated": frozenset({"name", "rewards"}),
    "promo.already": frozenset({"name"}),
    "promo.exhausted": frozenset({"name"}),
    "promo.expired": frozenset({"name"}),
    "promo.not_found": frozenset({"name"}),
    "promo.reward.cheston": frozenset({"amount"}),
    "promo.reward.cooldown_reset": frozenset(),
    "promo.reward.full_hunger": frozenset(),
    "promo.reward.heal": frozenset(),
    "promo.reward.hunger": frozenset({"percent"}),
    "promo.reward.progress": frozenset({"percent"}),
    "promo.reward.rc": frozenset({"amount"}),
    "promo.reward.stat": frozenset({"amount", "stat"}),
    "promo.reward.stat_capped": frozenset({"amount", "stat"}),
    "promo.usage": frozenset(),
    "quiz.correct": frozenset({"award", "minutes", "multiplier", "streak"}),
    "quiz.false_button": frozenset(),
    "quiz.not_active": frozenset(),
    "quiz.not_yours": frozenset(),
    "quiz.play_again": frozenset(),
    "quiz.result": frozenset({"answer", "choice", "status"}),
    "quiz.streak_broken": frozenset({"streak"}),
    "quiz.streak_expired": frozenset({"streak"}),
    "quiz.true_button": frozenset(),
    "quiz.true_false_title": frozenset(),
    "quiz.whois_title": frozenset(),
    "quiz.wrong": frozenset(),
    "quiz.wrong_streak": frozenset({"streak"}),
    "rich.download_failed": frozenset(),
    "rich.empty": frozenset(),
    "rich.not_utf8": frozenset(),
    "rich.rejected": frozenset({"error"}),
    "rich.too_long": frozenset({"limit"}),
    "rich.usage": frozenset(),
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
    "subscription.check_button": frozenset(),
    "subscription.confirmed": frozenset(),
    "subscription.not_yet": frozenset(),
    "subscription.required": frozenset({"channel"}),
    "subscription.required_alert": frozenset({"channel"}),
    "subscription.subscribe_button": frozenset(),
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
    "tops.power_title": frozenset({"count"}),
    "tops.power_value": frozenset({"power", "rank"}),
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
    "transfer.errors.bot": frozenset(),
    "transfer.errors.failed": frozenset(),
    "transfer.errors.insufficient_balance": frozenset(),
    "transfer.errors.not_a_person": frozenset(),
    "transfer.errors.receiver_limit": frozenset(),
    "transfer.errors.receiver_missing": frozenset(),
    "transfer.errors.receiver_vanished": frozenset(),
    "transfer.errors.self_transfer": frozenset(),
    "transfer.errors.sender_missing": frozenset(),
    "transfer.errors.sender_too_new": frozenset({"days"}),
    "transfer.errors.spouse": frozenset(),
    "transfer.reply_usage": frozenset(),
    "transfer.usage": frozenset(),
    "vocab.color.blue": frozenset(),
    "vocab.color.green": frozenset(),
    "vocab.color.red": frozenset(),
    "vocab.color.white": frozenset(),
    "vocab.color.yellow": frozenset(),
    "vocab.hunger.deadly": frozenset(),
    "vocab.hunger.full": frozenset(),
    "vocab.hunger.light": frozenset(),
    "vocab.hunger.strong": frozenset(),
    "vocab.kagune.bikaku": frozenset(),
    "vocab.kagune.koukaku": frozenset(),
    "vocab.kagune.rinkaku": frozenset(),
    "vocab.kagune.ukaku": frozenset(),
    "vocab.mob": frozenset(),
    "vocab.race.ccg": frozenset(),
    "vocab.race.ghoul": frozenset(),
    "vocab.race.human": frozenset(),
    "vocab.stat.dexterity": frozenset(),
    "vocab.stat.health": frozenset(),
    "vocab.stat.max_health": frozenset(),
    "vocab.stat.regeneration": frozenset(),
    "vocab.stat.speed": frozenset(),
    "vocab.stat.strength": frozenset(),
    "vocab.time.days": frozenset({"count"}),
    "vocab.time.hours": frozenset({"count"}),
    "vocab.time.minutes": frozenset({"count"}),
    "vocab.time.months": frozenset({"count"}),
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
