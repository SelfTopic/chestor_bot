from dataclasses import dataclass
from src.bot.services import BattleRecordService, DuelService
from src.bot.services.dialog import DialogService
from src.bot.services.language import LanguageService
from src.bot.session_services import SessionServices

from ....services.battle import BattleService

@dataclass(frozen=True)
class DuelServices:
    battle: BattleService
    battle_record_service: BattleRecordService
    duel_service: DuelService
    dialogs: DialogService
    languages: LanguageService

    @classmethod
    def from_services(cls, services: SessionServices) -> "DuelServices":
        return cls(
            battle=services.battle_service,
            battle_record_service=services.battle_record_service,
            duel_service=services.duel_service,
            dialogs=services.dialog_service,
            languages=services.language_service,
        )

