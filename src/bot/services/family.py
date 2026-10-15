from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum, auto

from src.bot.game_configs import MARRIAGE_CONFIG
from src.bot.utils import is_service_account
from src.database.models import FamilyRename, MarriageProposal

from ..repositories import ChatFamily, FamilyRepository, Member
from .user import UserService


class MarriageRefusal(Enum):
    SELF = auto()
    NOT_A_PERSON = auto()
    NOT_REGISTERED = auto()
    SAME_FAMILY = auto()
    TARGET_MARRIED = auto()
    ALREADY_PROPOSED = auto()
    NOT_ENOUGH_MONEY = auto()


class MarriageRefused(Exception):
    def __init__(self, reason: MarriageRefusal) -> None:
        super().__init__(reason.name)
        self.reason = reason


class ConsentRefusal(Enum):
    STALE = auto()
    NOT_INVITED = auto()
    ALREADY_CONSENTED = auto()
    NOT_ENOUGH_MONEY = auto()


class ConsentRefused(Exception):
    def __init__(self, reason: ConsentRefusal) -> None:
        super().__init__(reason.name)
        self.reason = reason


class MarriageFailure(Enum):
    TARGET_TAKEN = auto()
    FAMILY_CHANGED = auto()
    TARGET_BROKE = auto()


class NotMarried(Exception):
    pass


class RenameRefusal(Enum):
    NOT_MARRIED = auto()
    BAD_NAME = auto()
    ALREADY_PENDING = auto()


class RenameRefused(Exception):
    def __init__(self, reason: RenameRefusal) -> None:
        super().__init__(reason.name)
        self.reason = reason


@dataclass(frozen=True)
class RenameState:
    rename: FamilyRename
    # Нынешние члены семьи: согласиться должен каждый.
    members: tuple[int, ...]

    @property
    def consented(self) -> frozenset[int]:
        return frozenset(self.rename.consented)

    @property
    def renamed(self) -> bool:
        return self.rename.stage == "renamed"


@dataclass(frozen=True)
class ProposalState:
    proposal: MarriageProposal
    # Предлагающий, новенький, затем остальные члены семьи предлагающего.
    required: tuple[int, ...]
    consented: frozenset[int]
    failure: MarriageFailure | None = None

    @property
    def family_members(self) -> tuple[int, ...]:
        return self.required[2:]

    @property
    def married(self) -> bool:
        return self.proposal.stage == "married"


@dataclass(frozen=True)
class FamilyView:
    family_id: int
    name: str | None
    balance: int
    created_at: datetime
    members: list[Member]


@dataclass(frozen=True)
class Divorce:
    remaining: list[int]
    # Остался один человек: семья распалась, счёт семьи стал его личным.
    heir: int | None
    inherited: int


class FamilyService:
    def __init__(self, families: FamilyRepository, users: UserService) -> None:
        self._families = families
        self._users = users

    async def check_proposal(self, proposer_id: int, target_id: int) -> None:
        if proposer_id == target_id:
            raise MarriageRefused(MarriageRefusal.SELF)
        if is_service_account(proposer_id) or is_service_account(target_id):
            raise MarriageRefused(MarriageRefusal.NOT_A_PERSON)

        proposer = await self._users.get(proposer_id)
        if proposer is None or await self._users.get(target_id) is None:
            raise MarriageRefused(MarriageRefusal.NOT_REGISTERED)

        target_family = await self._families.family_id_of(target_id)
        if target_family is not None:
            same = target_family == await self._families.family_id_of(proposer_id)
            raise MarriageRefused(
                MarriageRefusal.SAME_FAMILY if same else MarriageRefusal.TARGET_MARRIED
            )

        if await self._families.has_awaiting(proposer_id, target_id):
            raise MarriageRefused(MarriageRefusal.ALREADY_PROPOSED)

        if await self._users.balance(proposer_id) < MARRIAGE_CONFIG.proposal_price:
            raise MarriageRefused(MarriageRefusal.NOT_ENOUGH_MONEY)

    async def propose(self, proposer_id: int, target_id: int, chat_id: int) -> ProposalState:
        await self.check_proposal(proposer_id, target_id)

        paid = await self._users.debit_if_sufficient(
            proposer_id, MARRIAGE_CONFIG.proposal_price, log=f"marriage proposal to {target_id}"
        )
        if paid is None:
            raise MarriageRefused(MarriageRefusal.NOT_ENOUGH_MONEY)

        family_id = await self._families.family_id_of(proposer_id)
        proposal = await self._families.create_proposal(
            proposer_id, target_id, family_id, chat_id
        )
        return await self._state(proposal)

    async def set_message(self, proposal_id: int, message_id: int) -> None:
        await self._families.set_message(proposal_id, message_id)

    async def state(self, proposal_id: int) -> ProposalState | None:
        proposal = await self._families.proposal(proposal_id)
        return None if proposal is None else await self._state(proposal)

    async def consent(self, proposal_id: int, telegram_id: int) -> ProposalState:
        proposal = await self._families.lock_proposal(proposal_id)
        if proposal is None or proposal.stage != "awaiting":
            raise ConsentRefused(ConsentRefusal.STALE)

        state = await self._state(proposal)
        if telegram_id not in state.required:
            raise ConsentRefused(ConsentRefusal.NOT_INVITED)
        if telegram_id in state.consented:
            raise ConsentRefused(ConsentRefusal.ALREADY_CONSENTED)
        if telegram_id == proposal.target_telegram_id:
            if await self._users.balance(telegram_id) < MARRIAGE_CONFIG.acceptance_price:
                raise ConsentRefused(ConsentRefusal.NOT_ENOUGH_MONEY)

        await self._families.add_consent(proposal_id, telegram_id)
        state = replace(state, consented=state.consented | {telegram_id})
        if set(state.required) <= state.consented:
            return await self._marry(state)
        return state

    async def decline(self, proposal_id: int, telegram_id: int) -> ProposalState:
        proposal = await self._families.lock_proposal(proposal_id)
        if proposal is None or proposal.stage != "awaiting":
            raise ConsentRefused(ConsentRefusal.STALE)

        state = await self._state(proposal)
        if telegram_id not in state.required[1:]:
            raise ConsentRefused(ConsentRefusal.NOT_INVITED)

        declined = await self._families.finish(proposal_id, "declined", declined_by=telegram_id)
        assert declined is not None
        return replace(state, proposal=declined)

    async def _marry(self, state: ProposalState) -> ProposalState:
        proposal = state.proposal
        proposer, target = proposal.proposer_telegram_id, proposal.target_telegram_id
        await self._families.lock_users(set(state.required))

        if await self._families.family_id_of(target) is not None:
            return await self._fail(state, MarriageFailure.TARGET_TAKEN)
        if await self._families.family_id_of(proposer) != proposal.family_id:
            return await self._fail(state, MarriageFailure.FAMILY_CHANGED)

        # Пока ждали блокировку, в семью мог вступить кто-то ещё: его согласие тоже нужно.
        fresh = await self._state(proposal)
        if not set(fresh.required) <= fresh.consented:
            return fresh

        paid = await self._users.debit_if_sufficient(
            target, MARRIAGE_CONFIG.acceptance_price, log=f"marriage with {proposer}"
        )
        if paid is None:
            return await self._fail(state, MarriageFailure.TARGET_BROKE)

        family_id = proposal.family_id
        if family_id is None:
            family_id = (await self._families.create_family()).id
            await self._join(family_id, proposer)
        await self._join(family_id, target)

        married = await self._families.finish(proposal.id, "married")
        assert married is not None
        return replace(fresh, proposal=married)

    # Деньги снимаются, пока человек ещё свободен и его кошелёк — личный баланс; после
    # вступления тот же вызов списал бы со счёта семьи.
    async def _join(self, family_id: int, telegram_id: int) -> None:
        amount = await self._users.balance(telegram_id)
        if amount:
            await self._users.minus_balance(telegram_id, amount, log=f"to family {family_id}")
        await self._families.add_member(family_id, telegram_id)
        if amount:
            await self._families.change_balance(family_id, amount)

    async def _fail(self, state: ProposalState, failure: MarriageFailure) -> ProposalState:
        failed = await self._families.finish(state.proposal.id, "failed")
        assert failed is not None
        return replace(state, proposal=failed, failure=failure)

    async def _state(self, proposal: MarriageProposal) -> ProposalState:
        proposer, target = proposal.proposer_telegram_id, proposal.target_telegram_id
        family = []
        if proposal.family_id is not None:
            members = await self._families.members(proposal.family_id)
            family = [m.telegram_id for m in members if m.telegram_id != proposer]
        consented = await self._families.consents(proposal.id)
        return ProposalState(proposal, (proposer, target, *family), frozenset(consented))

    async def family(self, telegram_id: int) -> FamilyView | None:
        family_id = await self._families.family_id_of(telegram_id)
        if family_id is None:
            return None
        family = await self._families.family(family_id)
        assert family is not None
        members = await self._families.members(family_id)
        return FamilyView(family_id, family.name, family.balance, family.created_at, members)

    async def divorce(self, telegram_id: int) -> Divorce:
        family_id = await self._families.family_id_of(telegram_id)
        if family_id is None:
            raise NotMarried()
        members = await self._families.members(family_id)
        await self._families.lock_users({m.telegram_id for m in members})
        if await self._families.family_id_of(telegram_id) != family_id:
            raise NotMarried()

        await self._families.remove_member(telegram_id)
        remaining = [m.telegram_id for m in await self._families.members(family_id)]
        if len(remaining) != 1:
            return Divorce(remaining, heir=None, inherited=0)

        (heir,) = remaining
        inherited = await self._families.dissolve(family_id)
        await self._families.remove_member(heir)
        if inherited:
            await self._users.plus_balance(heir, inherited, log=f"family {family_id} dissolved")
        return Divorce(remaining, heir=heir, inherited=inherited)

    async def expire_overdue(self) -> list[MarriageProposal]:
        lifetime = timedelta(seconds=MARRIAGE_CONFIG.proposal_lifetime_seconds)
        expired = []
        for proposal_id in await self._families.overdue(lifetime):
            proposal = await self._families.finish(proposal_id, "expired")
            if proposal is not None:
                expired.append(proposal)
        return expired

    async def families_in_chat(self, chat_id: int) -> list[ChatFamily]:
        return await self._families.families_in_chat(chat_id)

    async def propose_rename(self, proposer_id: int, raw_name: str, chat_id: int) -> RenameState:
        name = " ".join(raw_name.split())
        if not 0 < len(name) <= MARRIAGE_CONFIG.family_name_max_length:
            raise RenameRefused(RenameRefusal.BAD_NAME)
        family_id = await self._families.family_id_of(proposer_id)
        if family_id is None:
            raise RenameRefused(RenameRefusal.NOT_MARRIED)
        if await self._families.awaiting_rename(family_id) is not None:
            raise RenameRefused(RenameRefusal.ALREADY_PENDING)

        rename = await self._families.create_rename(family_id, name, proposer_id, chat_id)
        return await self._rename_state(rename)

    async def set_rename_message(self, rename_id: int, message_id: int) -> None:
        await self._families.set_rename_message(rename_id, message_id)

    async def rename_state(self, rename_id: int) -> RenameState | None:
        rename = await self._families.rename(rename_id)
        return None if rename is None else await self._rename_state(rename)

    async def answer_rename(self, rename_id: int, telegram_id: int, agree: bool) -> RenameState:
        rename = await self._families.lock_rename(rename_id)
        if rename is None or rename.stage != "awaiting":
            raise ConsentRefused(ConsentRefusal.STALE)
        state = await self._rename_state(rename)
        if not state.members:
            raise ConsentRefused(ConsentRefusal.STALE)
        if telegram_id not in state.members:
            raise ConsentRefused(ConsentRefusal.NOT_INVITED)

        if not agree:
            declined = await self._families.finish_rename(rename_id, "declined", telegram_id)
            assert declined is not None
            return replace(state, rename=declined)

        if telegram_id in state.consented:
            raise ConsentRefused(ConsentRefusal.ALREADY_CONSENTED)
        rename = await self._families.add_rename_consent(rename_id, telegram_id)
        if set(state.members) <= set(rename.consented):
            await self._families.set_name(rename.family_id, rename.name)
            renamed = await self._families.finish_rename(rename_id, "renamed")
            assert renamed is not None
            rename = renamed
        return replace(state, rename=rename)

    async def _rename_state(self, rename: FamilyRename) -> RenameState:
        members = [m.telegram_id for m in await self._families.members(rename.family_id)]
        proposer = rename.proposer_telegram_id
        ordered = [proposer] if proposer in members else []
        ordered += [tid for tid in members if tid != proposer]
        return RenameState(rename, tuple(ordered))

    async def expire_overdue_renames(self) -> list[RenameState]:
        lifetime = timedelta(seconds=MARRIAGE_CONFIG.proposal_lifetime_seconds)
        expired = []
        for rename_id in await self._families.overdue_renames(lifetime):
            rename = await self._families.finish_rename(rename_id, "expired")
            if rename is not None:
                expired.append(await self._rename_state(rename))
        return expired
