import logging
import random
import time
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass
from functools import cached_property

from selfrot import BaseContext, TEvent
from selfrot.exceptions import TelegramBadRequest
from selfrot.types import InputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container
from src.bot.dialogs import Line
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
from src.bot.types import MediaDownloadType, TimeComponents
from src.bot.utils import parse_seconds
from src.database.models import Ghoul, Media, User

from .repositories.fight import FightRepository
from .repositories.user_names import UserNameRepository
from .services.battle import BattleService
from .services.broadcast import BroadcastService
from .services.level_up import LevelUpService
from .services.lookup import find_user
from .services.media_paths import media_for, random_file
from .services.notify import Notifier, SelfrotBotNotifier
from .services.quiz import QuizService

logger = logging.getLogger(__name__)

# Лимит Telegram на подпись к медиа; длинный текст уходит без гифки.
CAPTION_LIMIT = 1024
_GIF_RANDOM = random.Random()


@dataclass(frozen=True)
class Addressee:
    telegram_id: int
    first_name: str


# Сервисы создаются лениво, один раз на апдейт. Сессию БД кладёт DatabaseMiddleware уже
# после create_context, поэтому в after_handle и отложенных вызовах сервисы с БД недоступны.
@dataclass
class AppContext(BaseContext[TEvent]):
    dialog_service: DialogService
    container: Container
    session_factory: async_sessionmaker[AsyncSession]
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
        return self.container.battle_engine()

    @cached_property
    def battle_service(self) -> BattleService:
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
        return self.container.media_repository()

    @cached_property
    def notifier(self) -> Notifier:
        return SelfrotBotNotifier(self.bot)

    @cached_property
    def broadcast_service(self) -> BroadcastService:
        # Не из контейнера: Notifier живёт на Bot этого апдейта.
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

    def text(self, line: Line) -> str:
        return self.dialog_service.text(line)

    async def db_user(self) -> User:
        sender = self.user
        user = await self.user_service.get(sender.id) if sender is not None else None

        if user is None:
            logger.error("User not found in database")
            raise ValueError("User not found in database")

        return user

    async def first_names(self, telegram_ids: Collection[int]) -> dict[int, str]:
        return await UserNameRepository(self.container.db_session()).first_names(
            telegram_ids
        )

    async def db_ghoul(self) -> Ghoul:
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
        event = self.event
        if isinstance(event, Message):
            replied = event.reply_to_message
            if replied is not None and replied.user is not None:
                return Addressee(replied.user.id, replied.user.first_name)

        if "@" not in mention:
            return None

        user = await find_user(self.user_service, mention)
        if user is None:
            raise UserNotFound(mention.lstrip("@"))

        return Addressee(user.telegram_id, user.first_name)

    async def say(
        self,
        line: Line,
        *,
        reply: bool = False,
        parse_mode: str | None = None,
    ) -> Message:
        text = self.text(line)
        media = await self._phrase_gif(line) if len(text) <= CAPTION_LIMIT else None
        if media is not None:
            send_gif = self.reply_animation if reply else self.answer_animation
            return await self._send_gif(send_gif, media, text, parse_mode=parse_mode)

        send = self.reply_message if reply else self.answer_message
        return await send(text, parse_mode=parse_mode)

    # Своя сессия: say() зовут и из on_error / defer, где сессии апдейта уже нет.
    async def _phrase_gif(self, line: Line) -> Media | None:
        gifs = self.dialog_service.gifs(line)
        if gifs.chance < 1 and _GIF_RANDOM.random() >= gifs.chance:
            return None

        path = random_file(gifs.folder)
        if path is None:
            return None

        registered_by = self.user.id if self.user is not None else 0
        async with self.session_factory() as session:
            media = await media_for(
                MediaRepository(session),
                path,
                MediaDownloadType.ANIMATION,
                line.key,
                registered_by,
            )
            await session.commit()
        return media

    async def _send_gif(
        self,
        send: Callable[..., Awaitable[Message]],
        media: Media,
        caption: str,
        *,
        parse_mode: str | None = None,
    ) -> Message:
        options = {"caption": caption, "parse_mode": parse_mode}
        try:
            sent = await send(
                animation=media.telegram_file_id or InputFile.from_path(media.path),
                **options,
            )
        except TelegramBadRequest:
            sent = await send(animation=InputFile.from_path(media.path), **options)
        else:
            if media.telegram_file_id:
                return sent

        if sent.animation is not None:
            async with self.session_factory() as session:
                await MediaRepository(session).update_file_id(
                    path=media.path, new_file_id=sent.animation.file_id
                )
                await session.commit()
        return sent

    async def answer_gif(self, media: Media, caption: str = "") -> Message:
        return await self._send_gif(self.answer_animation, media, caption)

    async def reply_gif(self, media: Media, caption: str = "") -> Message:
        return await self._send_gif(self.reply_animation, media, caption)

    async def cooldown_remaining(
        self, telegram_id: int, cooldown_name: str
    ) -> TimeComponents | None:
        cooldown = await self.cooldown_service.get_active_cooldown(
            telegram_id, cooldown_name
        )
        if cooldown is None:
            return None

        return parse_seconds(int(cooldown.end_at - time.time()))
