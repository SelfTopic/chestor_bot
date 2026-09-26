"""
Бои порта: участники → бойцы → бой → последствия → счёт. Без Telegram: роутер
получает итог одним объектом и сам решает, что и куда отправить.

Движок и мост к нему (гуль → боец, бой, здоровье после боя) — прод-BattleService,
здесь он называется engine и переиспользуется как есть. Этот сервис собирает то,
что прод размазал по fight.py и mob_battle.py: загрузку участников, запись
здоровья, награды, историю, лок ActiveBattle и стадии дуэли. Числа, порядок
записей и правила — как у прода.
"""

import logging
import random
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto

from src.bot.exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from src.bot.game_configs import DUEL_CONFIG, MOB_CONFIG
from src.bot.services import (
    BattleEngine,
    BattleRecordService,
    DuelService,
    GhoulService,
    UserService,
)
from src.bot.services.battle_engine.core import BattleResult, Fighter
from src.bot.utils import utcnow_naive
from src.database.models import DuelSession, Ghoul, User

from ..repositories.battle import FightRepository, Score
from .level_up import LevelUpService

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Combatant:
    user: User
    ghoul: Ghoul

    @property
    def telegram_id(self) -> int:
        return self.user.telegram_id

    @property
    def name(self) -> str:
        return self.user.full_name


@dataclass(frozen=True)
class FightReport:
    """Всё, что нужно, чтобы показать бой (BattleTextGenerator)."""

    result: BattleResult
    fighter_a: Fighter
    fighter_b: Fighter
    rank_a: str
    rank_b: str

    @property
    def winner(self) -> str | None:
        """ "a", "b" или None — ничья."""
        return self.result.winner


class DuelRefusal(Enum):
    """Почему дуэль нельзя начать; проверки идут в этом порядке, как у прода."""

    SELF = auto()
    NOT_REGISTERED = auto()
    INITIATOR_NO_PRIVATE_CHAT = auto()
    TARGET_NO_PRIVATE_CHAT = auto()
    INITIATOR_NO_GHOUL = auto()
    TARGET_NO_GHOUL = auto()
    DEAD = auto()
    NOT_COMBAT_READY = auto()
    BUSY = auto()
    PAIR_LIMIT = auto()
    INITIATOR_DAY_LIMIT = auto()
    TARGET_DAY_LIMIT = auto()
    CLAIM_FAILED = auto()


class DuelRefused(Exception):
    def __init__(self, reason: DuelRefusal, *, health: int = 0, threshold: int = 0) -> None:
        super().__init__(reason.name)
        self.reason = reason
        # только у NOT_COMBAT_READY: текущее здоровье и нужный минимум
        self.health = health
        self.threshold = threshold


@dataclass(frozen=True)
class OpenedDuel:
    session: DuelSession
    initiator_name: str
    target_name: str


@dataclass(frozen=True)
class DuelOdds:
    """Расклад сил перед дуэлью: нужен ли выбор "всерьёз/фора" и у кого."""

    power_ratio: float
    favored_telegram_id: int

    @property
    def needs_fora_choice(self) -> bool:
        return self.power_ratio >= DUEL_CONFIG.power_ratio_threshold


@dataclass(frozen=True)
class DuelFight:
    report: FightReport
    winner_telegram_id: int | None
    loser_telegram_id: int | None
    reward_level_progress: float | None


@dataclass(frozen=True)
class DuelOutcome:
    """Итог выбора победителя. Суммы None — наград этого вида не было."""

    action: str  # "outcome_rob" | "outcome_eat" | "outcome_release"
    winner_name: str
    loser_name: str
    reward_balance: int | None
    reward_rc: int | None
    hunger_restored: int | None
    reward_level_progress: float | None
    winner_score: Score
    loser_score: Score


@dataclass(frozen=True)
class MobFight:
    report: FightReport
    reward_level_progress: float | None
    reward_rc: int | None
    reward_cheston: int | None


class BattleService:
    def __init__(
        self,
        engine: BattleEngine,
        fights: FightRepository,
        ghoul_service: GhoulService,
        user_service: UserService,
        level_up_service: LevelUpService,
        battle_record_service: BattleRecordService,
        duel_service: DuelService,
    ) -> None:
        self.engine = engine
        self._fights = fights
        self._ghouls = ghoul_service
        self._users = user_service
        self._level_up = level_up_service
        self._records = battle_record_service
        self._duels = duel_service

    # --- Общее --------------------------------------------------------------

    async def _combatants(self, *telegram_ids: int) -> list[Combatant] | None:
        """Участники в порядке telegram_ids с досчитанными пассивными статами, как
        после GhoulService.get; None, если у кого-то нет пользователя или гуля."""
        found = await self._fights.participants(*telegram_ids)
        combatants = []
        for telegram_id in telegram_ids:
            user, ghoul = found.get(telegram_id, (None, None))
            if user is None or ghoul is None:
                return None
            ghoul = await self._ghouls.materialize_passive_stats(ghoul)
            combatants.append(Combatant(user, ghoul))
        return combatants

    def _fighter(self, combatant: Combatant, name: str | None = None) -> Fighter:
        return self.engine.ghoul_to_fighter(
            combatant.ghoul, name or combatant.name, self._ghouls
        )

    def _rank(self, fighter: Fighter) -> str:
        return self._ghouls.get_danger_rank(self.engine.power_of(fighter.snapshot))

    def _report(self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter) -> FightReport:
        return FightReport(
            result, fighter_a, fighter_b, self._rank(fighter_a), self._rank(fighter_b)
        )

    async def _save_health(
        self, combatant: Combatant, effective_max: float, final_hp: float
    ) -> None:
        health = BattleEngine.resolve_post_battle_health(
            combatant.ghoul.health, effective_max, final_hp
        )
        # health_updated_at двигается вместе с health: иначе следующий
        # materialize_passive_stats досчитает реген от старой метки поверх урона.
        await self._ghouls.set_fields(
            combatant.telegram_id, health=health, health_updated_at=utcnow_naive()
        )

    async def score(self, telegram_id: int, battle_type: str) -> Score:
        return (await self._fights.scores([telegram_id], battle_type))[telegram_id]

    # --- Дуэль --------------------------------------------------------------

    async def _abort_duel(self, duel: DuelSession, expected_stage: str) -> None:
        """Участник исчез между шагами: снять лок и закрыть дуэль."""
        logger.error("duel %s: participant vanished at %s", duel.id, expected_stage)
        await self._records.release(duel.initiator_telegram_id, duel.target_telegram_id)
        await self._duels.atomic_update(duel.id, expected_stage, stage="done")

    async def open_duel(
        self, initiator_id: int, target_id: int, *, chat_id: int, private: bool
    ) -> OpenedDuel:
        """Все проверки приглашения, лок ActiveBattle и DuelSession на стадии согласия.
        Отказ — DuelRefused с первой не прошедшей проверкой."""
        if target_id == initiator_id:
            raise DuelRefused(DuelRefusal.SELF)

        found = await self._fights.participants(initiator_id, target_id)
        if initiator_id not in found or target_id not in found:
            raise DuelRefused(DuelRefusal.NOT_REGISTERED)
        initiator_user, initiator_ghoul = found[initiator_id]
        target_user, target_ghoul = found[target_id]

        # Без лички некуда доставить секретный выбор "всерьёз/фора".
        if not initiator_user.has_private_chat:
            raise DuelRefused(DuelRefusal.INITIATOR_NO_PRIVATE_CHAT)
        if not target_user.has_private_chat:
            raise DuelRefused(DuelRefusal.TARGET_NO_PRIVATE_CHAT)

        if initiator_ghoul is not None:
            initiator_ghoul = await self._ghouls.materialize_passive_stats(initiator_ghoul)
        if target_ghoul is not None:
            target_ghoul = await self._ghouls.materialize_passive_stats(target_ghoul)
        if initiator_ghoul is None:
            raise DuelRefused(DuelRefusal.INITIATOR_NO_GHOUL)
        if target_ghoul is None:
            raise DuelRefused(DuelRefusal.TARGET_NO_GHOUL)

        try:
            await self.engine.validate_duel(
                initiator_ghoul,
                target_ghoul,
                has_pending_confirmation=lambda g: self._records.is_busy(g.telegram_id),
            )
        except FighterIsDeadError:
            raise DuelRefused(DuelRefusal.DEAD) from None
        except FighterNotCombatReadyError as exc:
            raise DuelRefused(
                DuelRefusal.NOT_COMBAT_READY, health=exc.health, threshold=exc.threshold
            ) from None
        except FighterHasPendingBattleError:
            raise DuelRefused(DuelRefusal.BUSY) from None

        # Дневные лимиты (BATTLE_ENGINE.md 1.2/4.4).
        recent = await self._fights.recent_battles(
            initiator_id, target_id, since=utcnow_naive() - timedelta(days=1)
        )
        if recent.pair >= DUEL_CONFIG.max_battles_per_day_pair:
            raise DuelRefused(DuelRefusal.PAIR_LIMIT)
        if recent.initiator >= DUEL_CONFIG.max_battles_per_day_total:
            raise DuelRefused(DuelRefusal.INITIATOR_DAY_LIMIT)
        if recent.target >= DUEL_CONFIG.max_battles_per_day_total:
            raise DuelRefused(DuelRefusal.TARGET_DAY_LIMIT)

        if not await self._records.try_claim_duel(initiator_id, target_id):
            raise DuelRefused(DuelRefusal.CLAIM_FAILED)

        session = await self._duels.create(
            chat_id=chat_id,
            initiator_telegram_id=initiator_id,
            target_telegram_id=target_id,
            is_private_origin=private,
        )
        return OpenedDuel(session, initiator_user.full_name, target_user.full_name)

    async def duel_odds(self, duel: DuelSession) -> DuelOdds | None:
        """Расклад сил после согласия обеих сторон; None — дуэль закрыта, участник исчез."""
        combatants = await self._combatants(duel.initiator_telegram_id, duel.target_telegram_id)
        if combatants is None:
            await self._abort_duel(duel, "awaiting_consent")
            return None

        initiator, target = combatants
        power_a = self.engine.power_of(self._fighter(initiator, "a").snapshot)
        power_b = self.engine.power_of(self._fighter(target, "b").snapshot)
        weaker, stronger = min(power_a, power_b), max(power_a, power_b)
        return DuelOdds(
            power_ratio=stronger / weaker if weaker > 0 else float("inf"),
            favored_telegram_id=(
                initiator.telegram_id if power_a >= power_b else target.telegram_id
            ),
        )

    async def fight_duel(self, duel: DuelSession) -> DuelFight | None:
        """Бой, здоровье после боя и опыт победителю. None — участник исчез, дуэль
        закрыта. Историю и стадию записывает finish_duel_fight, когда бой объявлен."""
        combatants = await self._combatants(duel.initiator_telegram_id, duel.target_telegram_id)
        if combatants is None:
            await self._abort_duel(duel, "running")
            return None

        initiator, target = combatants
        fighter_a, fighter_b = self._fighter(initiator), self._fighter(target)
        compress_hp = duel.compress_hp if duel.compress_hp is not None else True
        result = self.engine.run_duel(fighter_a, fighter_b, compress_hp=compress_hp)

        await self._save_health(initiator, result.stats_a.health, result.final_hp_a)
        await self._save_health(target, result.stats_b.health, result.final_hp_b)
        report = self._report(result, fighter_a, fighter_b)

        if result.winner is None:
            return DuelFight(report, None, None, None)

        winner, loser = (initiator, target) if result.winner == "a" else (target, initiator)
        winner_power = self._ghouls.calculate_power(winner.ghoul)
        loser_power = self._ghouls.calculate_power(loser.ghoul)
        # Формула левел-апа (BATTLE_DESIGN.md): 1% * (сила соперника / своя сила).
        progress = 1.0 * loser_power / winner_power if winner_power > 0 else 0.0
        await self._level_up.add_progress(winner.telegram_id, progress)
        return DuelFight(report, winner.telegram_id, loser.telegram_id, progress)

    async def finish_duel_fight(
        self, duel: DuelSession, fight: DuelFight, outcome_message_id: int | None
    ) -> DuelSession | None:
        """После объявления боя: у ничьей история сразу и дуэль закрыта, иначе ждём
        выбор победителя (его таймаут ведёт DuelTicker)."""
        result = fight.report.result
        if fight.winner_telegram_id is None or fight.loser_telegram_id is None:
            # Настоящая ничья (BATTLE_ENGINE.md 2.6): выбирать нечего.
            await self._records.record_duel(
                duel.initiator_telegram_id,
                duel.target_telegram_id,
                winner=None,
                ended_naturally=result.ended_naturally,
                is_forced=False,
            )
            await self._records.release(duel.initiator_telegram_id, duel.target_telegram_id)
            return await self._duels.atomic_update(duel.id, "running", stage="done")

        return await self._duels.atomic_update(
            duel.id,
            "running",
            stage="awaiting_winner_choice",
            winner_telegram_id=fight.winner_telegram_id,
            loser_telegram_id=fight.loser_telegram_id,
            outcome_message_id=outcome_message_id,
            reward_level_progress=fight.reward_level_progress,
            ended_naturally=result.ended_naturally,
        )

    async def resolve_duel_outcome(self, duel: DuelSession, action: str) -> DuelOutcome:
        """Исход "ограбить/отпустить/съесть", история, снятие лока и счёт уже с этим
        боем. Вызывать, только когда atomic_update перевёл дуэль в "done" с этим
        выбором: из гонки нажатия и таймаута сюда попадает кто-то один."""
        assert duel.winner_telegram_id is not None
        assert duel.loser_telegram_id is not None
        winner_id, loser_id = duel.winner_telegram_id, duel.loser_telegram_id

        found = await self._fights.participants(winner_id, loser_id)
        winner_user, _ = found.get(winner_id, (None, None))
        loser_user, loser_ghoul = found.get(loser_id, (None, None))

        reward_balance = reward_rc = hunger_restored = None
        if action == "outcome_rob":
            reward_balance = await self._rob(winner_id, loser_id, loser_user)
        elif action == "outcome_eat":
            reward_rc, hunger_restored = await self._eat(winner_id, loser_id, loser_ghoul)

        await self._records.record_duel(
            duel.initiator_telegram_id,
            duel.target_telegram_id,
            winner="a" if winner_id == duel.initiator_telegram_id else "b",
            ended_naturally=duel.ended_naturally if duel.ended_naturally is not None else True,
            is_forced=False,
            winner_choice=action.removeprefix("outcome_"),
            reward_level_progress=duel.reward_level_progress,
            reward_rc=reward_rc,
            reward_balance=reward_balance,
        )
        await self._records.release(duel.initiator_telegram_id, duel.target_telegram_id)

        scores = await self._fights.scores([winner_id, loser_id], "duel")
        return DuelOutcome(
            action=action,
            winner_name=winner_user.full_name if winner_user else str(winner_id),
            loser_name=loser_user.full_name if loser_user else str(loser_id),
            reward_balance=reward_balance,
            reward_rc=reward_rc,
            hunger_restored=hunger_restored,
            reward_level_progress=duel.reward_level_progress,
            winner_score=scores[winner_id],
            loser_score=scores[loser_id],
        )

    async def _rob(self, winner_id: int, loser_id: int, loser: User | None) -> int | None:
        if loser is None or loser.balance <= 0:
            return None
        percent = random.uniform(DUEL_CONFIG.rob_percent_min, DUEL_CONFIG.rob_percent_max)
        amount = round(loser.balance * percent / 100.0)
        if amount <= 0:
            return None
        await self._users.minus_balance(loser_id, amount, log=f"duel robbery by {winner_id}")
        await self._users.plus_balance(winner_id, amount, log=f"duel robbery from {loser_id}")
        return amount

    async def _eat(
        self, winner_id: int, loser_id: int, loser: Ghoul | None
    ) -> tuple[int | None, int | None]:
        """RC-клетки с тела и восстановленный голод победителя."""
        reward_rc = None
        if loser is not None:
            loser = await self._ghouls.materialize_passive_stats(loser)
            rc = round(
                self._ghouls.calculate_power(loser)
                * random.uniform(DUEL_CONFIG.eat_rc_multiplier_min, DUEL_CONFIG.eat_rc_multiplier_max)
            )
            if rc > 0:
                await self._ghouls.increment_fields(winner_id, rc_money=rc)
                reward_rc = rc
        await self._ghouls.apply_death(loser_id, cause="eaten", killer_telegram_id=winner_id)
        # apply_death трогает только проигравшего: счётчик съеденных гулей и голод
        # победителя ведутся отдельно (те же проценты, что у "сожрать человека").
        await self._ghouls.increment_fields(winner_id, eat_ghouls=1)
        _, hunger_restored = await self._ghouls.restore_hunger_from_eating(winner_id)
        return reward_rc, hunger_restored

    # --- Моб ----------------------------------------------------------------

    async def fight_mob(
        self, user: User, ghoul: Ghoul, *, is_forced: bool, reward_log: str
    ) -> MobFight:
        """Бой с мобом ("бить моба" или засада в "сожрать человека"): здоровье,
        награды за победу, история и снятие лока. Лок берёт вызывающий: у засады
        "занят" значит "засады не было", а у "бить моба" это отказ."""
        player = Combatant(user, ghoul)
        fighter = self._fighter(player)
        result, mob = self.engine.run_against_mob(fighter)
        await self._save_health(player, result.stats_a.health, result.final_hp_a)

        reward_level_progress = reward_rc = reward_cheston = None
        if result.winner == "a":
            mob_power = self.engine.power_of(mob.snapshot)
            player_power = self._ghouls.calculate_power(ghoul)
            # BATTLE_DESIGN.md "Формула левел-апа": как у дуэли, но ÷5 — фарм мобов
            # медленнее PvP.
            reward_level_progress = (
                (mob_power / player_power) / MOB_CONFIG.level_progress_divisor
                if player_power > 0
                else 0.0
            )
            await self._level_up.add_progress(player.telegram_id, reward_level_progress)

            if random.random() < MOB_CONFIG.rc_drop_chance:
                reward_rc = random.randint(MOB_CONFIG.rc_drop_min, MOB_CONFIG.rc_drop_max)
                await self._ghouls.increment_fields(player.telegram_id, rc_money=reward_rc)

            # ECONOMY.md часть 4: CheSton за победу привязан к цене прокачки
            # эталонного стата на текущем уровне.
            reward_cheston = MOB_CONFIG.cheston_reward_for_mob_win(ghoul.level)
            await self._users.plus_balance(
                player.telegram_id, change_balance=reward_cheston, log=reward_log
            )

        await self._records.record_mob_fight(
            telegram_id=player.telegram_id,
            mob_name=mob.name,
            winner=result.winner,
            ended_naturally=result.ended_naturally,
            is_forced=is_forced,
            reward_level_progress=reward_level_progress,
            reward_rc=reward_rc,
            reward_balance=reward_cheston,
        )
        await self._records.release(player.telegram_id)

        return MobFight(
            self._report(result, fighter, mob), reward_level_progress, reward_rc, reward_cheston
        )
