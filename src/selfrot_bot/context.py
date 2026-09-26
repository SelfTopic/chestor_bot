import logging
import time
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass
from functools import cached_property

from selfrot import BaseContext, TEvent
from selfrot.exceptions import TelegramBadRequest
from selfrot.types import InputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.exceptions import UserNotFound
from src.bot.services import (
    BanService,
    BattleEngine,
    BattleRecordService,
    ChatService,
    CoffeeService,
    CooldownService,
    DuelService,
    GhoulService,
    PlayerLookupService,
    ResetService,
    RpCommandsService,
    StatsEditService,
    TransferService,
    UserService,
    VideoCutterService,
    VideoWorker,
    WikipediaService,
    WordleService,
)
from src.bot.repositories import MediaRepository
from src.bot.services.dialog import DialogService
from src.bot.services.ghoul_game import LotteryService
from src.bot.services.stat_upgrade import StatUpgradeService
from src.bot.types import TimeComponents
from src.bot.utils import parse_seconds
from src.database.models import Ghoul, Media, User

from .repositories.battle import FightRepository
from .repositories.users import UserNameRepository
from .services.battle import BattleService
from .services.broadcast import BroadcastService
from .services.level_up import LevelUpService
from .services.lookup import find_user
from .services.notify import Notifier, SelfrotBotNotifier
from .services.quiz import QuizService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Addressee:
    """Кому адресована команда."""

    telegram_id: int
    first_name: str


@dataclass
class AppContext(BaseContext[TEvent]):
    """
    Контекст одного апдейта. Все зависимости хендлера лежат здесь, явно и с типами:
    хендлер берёт `self.ctx.transfer_service`, а не лезет в контейнер.

    Сервисы создаются лениво и один раз на апдейт (cached_property): контейнер
    привязывает их к сессии БД из session_context, а её кладёт DatabaseMiddleware,
    то есть уже ПОСЛЕ create_context. Поэтому обращаться к ним можно в фильтрах,
    мидлварях после Database и в handle, но не в after_handle и отложенных вызовах:
    к тому времени сессия закрыта (сервисы без БД, вроде video_worker, безопасны).
    Новый сервис добавляется сюда одной строкой; контейнер остаётся деталью реализации.
    """

    dialog_service: DialogService
    container: Container
    session_factory: async_sessionmaker[AsyncSession]
    # Не прод-GhoulQuizService из контейнера: один клиент ghoul_quiz 0.2 на
    # процесс, его держит Dispatcher (см. services/quiz.py).
    ghoul_quiz_service: QuizService

    @cached_property
    def user_service(self) -> UserService:
        return self.container.user_service()

    @cached_property
    def chat_service(self) -> ChatService:
        return self.container.chat_service()

    @cached_property
    def transfer_service(self) -> TransferService:
        return self.container.transfer_service()

    @cached_property
    def ghoul_service(self) -> GhoulService:
        return self.container.ghoul_service()

    @cached_property
    def coffee_service(self) -> CoffeeService:
        return self.container.coffee_service()

    @cached_property
    def stat_upgrade_service(self) -> StatUpgradeService:
        return self.container.stat_upgrade_service()

    @cached_property
    def battle_engine(self) -> BattleEngine:
        """Прод-мост к движку боя: гуль → боец, мощь, проверка готовности к бою."""
        return self.container.battle_engine()

    @cached_property
    def battle_service(self) -> BattleService:
        """Бои целиком: участники, бой, последствия, счёт (services/battle.py)."""
        return BattleService(
            engine=self.battle_engine,
            fights=FightRepository(
                self.container.db_session(), self.container.ghoul_repository()
            ),
            ghoul_service=self.ghoul_service,
            user_service=self.user_service,
            level_up_service=self.level_up_service,
            battle_record_service=self.battle_record_service,
            duel_service=self.duel_service,
        )

    @cached_property
    def duel_service(self) -> DuelService:
        return self.container.duel_service()

    @cached_property
    def battle_record_service(self) -> BattleRecordService:
        return self.container.battle_record_service()

    @cached_property
    def lottery_service(self) -> LotteryService:
        return self.container.lottery_service()

    @cached_property
    def rp_commands_service(self) -> RpCommandsService:
        return self.container.rp_commands_service()

    @cached_property
    def wordle_service(self) -> WordleService:
        return self.container.wordle_service()

    @cached_property
    def wikipedia_service(self) -> WikipediaService:
        return self.container.wikipedia_service()

    @cached_property
    def video_worker(self) -> VideoWorker:
        return self.container.video_worker()

    @cached_property
    def video_cutter_service(self) -> VideoCutterService:
        return self.container.video_cutter_service()

    @cached_property
    def ban_service(self) -> BanService:
        return self.container.ban_service()

    @cached_property
    def player_lookup_service(self) -> PlayerLookupService:
        return self.container.player_lookup_service()

    @cached_property
    def stats_edit_service(self) -> StatsEditService:
        return self.container.stats_edit_service()

    @cached_property
    def reset_service(self) -> ResetService:
        return self.container.reset_service()

    @cached_property
    def cooldown_service(self) -> CooldownService:
        return self.container.cooldown_service()

    @cached_property
    def media_repository(self) -> MediaRepository:
        # Не сервис: /add_gif сам сохраняет файл, а до БД добирается репозиторием.
        return self.container.media_repository()

    @cached_property
    def notifier(self) -> Notifier:
        return SelfrotBotNotifier(self.bot)

    @cached_property
    def broadcast_service(self) -> BroadcastService:
        # Не из Container: ему нужен Notifier, а тот живёт на Bot этого апдейта.
        return BroadcastService(
            self.container.user_repository(),
            self.container.chat_repository(),
            self.notifier,
        )

    @cached_property
    def level_up_service(self) -> LevelUpService:
        return LevelUpService(
            self.user_service, self.ghoul_service, self.dialog_service, self.notifier
        )

    async def db_user(self) -> User:
        """
        Отправитель апдейта как запись БД. Запись создаёт SyncEntitiesMiddleware до
        хендлера, поэтому её отсутствие это ошибка, а не обычный случай.
        """
        sender = self.user
        user = await self.user_service.get(sender.id) if sender is not None else None

        if user is None:
            logger.error("User not found in database")
            raise ValueError("User not found in database")

        return user

    async def first_names(self, telegram_ids: Collection[int]) -> dict[int, str]:
        """Имена игроков одним запросом (топы: прод брал каждого отдельным get)."""
        return await UserNameRepository(self.container.db_session()).first_names(
            telegram_ids
        )

    async def db_ghoul(self) -> Ghoul:
        """
        Гуль отправителя апдейта как запись БД. Существование и то, что он жив,
        гарантирует GhoulMiddleware до хендлера (весь ghoul_routers за ней), поэтому
        отсутствие здесь это ошибка, а не обычный случай — как и у db_user."""
        sender = self.user
        ghoul = (
            await self.ghoul_service.get(find_by=sender.id)
            if sender is not None
            else None
        )

        if ghoul is None:
            logger.error("Ghoul not found in database")
            raise ValueError("Ghoul not found in database")

        return ghoul

    async def addressee(self, mention: str = "") -> Addressee | None:
        """
        Кому адресована команда: автору сообщения, на которое ответили (имя берётся из
        самого Telegram-сообщения, человека в БД может и не быть), иначе @username из
        аргументов (он ищется в БД). None, если адресата нет: команда молчит.
        Неизвестный @username это UserNotFound.
        """
        event = self.event
        if isinstance(event, Message):
            replied = event.reply_to_message
            if replied is not None and replied.user is not None:
                return Addressee(replied.user.id, replied.user.first_name)

        if "@" not in mention:
            return None

        user = await find_user(self.user_service, mention)
        if user is None:
            raise UserNotFound(
                f"Пользователь с username {mention.lstrip('@')} не найден"
            )

        return Addressee(user.telegram_id, user.first_name)

    async def _send_gif(
        self, send: Callable[..., Awaitable[Message]], media: Media, caption: str
    ) -> Message:
        """
        Гиф с кэшем telegram_file_id: сперва уже известный id (дёшево, без аплоада),
        а если он протух (TelegramBadRequest — файл удалили из Telegram и т.п.),
        перезаливка с диска и новый id в кэш. Тот же приём, что уже есть у
        NotificationTicker для видео (media_paths.py/notification_ticker.py), включая
        прод-особенность: id кэшируется только веткой retry, не первой заливкой с
        диска, когда кэша ещё не было вовсе — сохранено как есть.
        """
        try:
            return await send(
                animation=media.telegram_file_id or InputFile.from_path(media.path),
                caption=caption,
            )
        except TelegramBadRequest:
            sent = await send(
                animation=InputFile.from_path(media.path), caption=caption
            )
            if sent.animation is not None:
                await self.media_repository.update_file_id(
                    path=media.path, new_file_id=sent.animation.file_id
                )
            return sent

    async def answer_gif(self, media: Media, caption: str = "") -> Message:
        """Гиф новым сообщением в чат апдейта (как ctx.answer_animation, но с кэшем
        file_id — см. _send_gif)."""
        return await self._send_gif(self.answer_animation, media, caption)

    async def reply_gif(self, media: Media, caption: str = "") -> Message:
        """Гиф в ответ на сообщение апдейта (как ctx.reply_animation, но с кэшем
        file_id — см. _send_gif)."""
        return await self._send_gif(self.reply_animation, media, caption)

    async def cooldown_remaining(
        self, telegram_id: int, cooldown_name: str
    ) -> TimeComponents | None:
        """
        None — telegram_id не на кулдауне cooldown_name. Иначе — сколько осталось
        (TimeComponents: days/hours_remaining/total_hours/minutes_remaining/
        seconds_remaining, см. src.bot.utils.parse_time). Только сам факт и остаток
        времени — текст ответа и ключ dialogs.json остаются на хендлере: у прода
        они не унифицированы (где-то есть hours, где-то нет, а mob_fight.py вообще
        отвечает жёстким текстом, не через DialogService), а такое различие — не
        то, что стоит скрывать хелпером.
        """
        cooldown = await self.cooldown_service.get_active_cooldown(
            telegram_id, cooldown_name
        )
        if cooldown is None:
            return None

        return parse_seconds(int(cooldown.end_at - time.time()))
