from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator
from selfrot import CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command
from selfrot.types import InputFile, Message

from src.bot.dialogs import Dialogs
from src.bot.services import VideoCutterService
from src.bot.types import VideoCutJob

from ....context import AppContext
from ...types import TextMessage
from .delivery import deliver_cut
from .guard import cut_guard


def _check_timecode(value: str) -> str:
    if not VideoCutterService.validate_time_format(value):
        raise ValueError("нужен формат ММ:СС")

    return value


TimeCode = Annotated[str, AfterValidator(_check_timecode)]


class AnimeArgs(CommandArgs):
    season: int
    episode: int
    start: TimeCode = ""
    end: TimeCode = ""
    gif: Literal["gif"] | None = None


class AnimeHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("anime", AnimeArgs)
    query = cmd
    end_error = Dialogs.anime.bad_end()
    start_error = Dialogs.anime.bad_start()
    format_error = Dialogs.anime.bad_format()
    usage = Dialogs.anime.usage()

    # Долгая часть (нарезка, загрузка) — в after_handle: к тому времени слот диспетчера и
    # сессия БД свободны.
    episode_path: Path | None = None
    job: VideoCutJob | None = None
    processing: Message | None = None
    is_gif = False
    user_id = 0

    async def handle(self) -> None:
        message = self.ctx.message
        args = self.cmd.parse(self.ctx)

        input_path = Path(
            f"src/assets/videos/tokio_ghoul/Season_{args.season}_Episode_{args.episode}.mp4"
        )

        if not input_path.exists():
            await message.answer(
                self.ctx.text(
                    Dialogs.anime.not_found(season=args.season, episode=args.episode)
                )
            )
            return

        if not args.start and not args.end:
            self.episode_path = input_path
            return

        if not args.start or not args.end:
            await message.answer(self.ctx.text(self.format_error))
            return

        video_cutter = self.ctx.video_cutter_service

        try:
            if video_cutter.parse_duration(args.start, args.end) <= 0:
                raise ValueError

        except ValueError:
            await message.answer(self.ctx.text(Dialogs.anime.end_before_start()))
            return

        user_id = message.user.id if message.user else message.chat.id

        if cut_guard.is_busy(user_id):
            await message.answer(self.ctx.text(Dialogs.anime.busy()))
            return

        # Занять место до первого await: иначе два быстрых /anime подряд пройдут проверку
        # оба.
        cut_guard.occupy(user_id)
        try:
            job = VideoCutJob(
                input_file_path=input_path,
                output_file_path=video_cutter.generate_output_path(
                    input_path.name, is_gif=args.gif is not None
                ),
                start_time=args.start,
                end_time=args.end,
                chat_id=message.chat.id,
                caption=self.ctx.text(
                    Dialogs.anime.cut_caption(
                        season=args.season,
                        episode=args.episode,
                        start=args.start,
                        end=args.end,
                    )
                ),
            )

            self.processing = await message.reply(
                self.ctx.text(
                    Dialogs.anime.cutting(
                        season=args.season,
                        episode=args.episode,
                        start=args.start,
                        end=args.end,
                    )
                )
            )
        except BaseException:
            cut_guard.release(user_id)
            raise

        self.job = job
        self.is_gif = args.gif is not None
        self.user_id = user_id

    async def after_handle(self) -> None:
        if self.episode_path is not None:
            args = self.cmd.parse(self.ctx)
            await self.ctx.message.reply_video(
                video=InputFile.from_path(self.episode_path),
                caption=self.ctx.text(
                    Dialogs.anime.episode_caption(
                        season=args.season, episode=args.episode
                    )
                ),
            )
            return

        if self.job is None or self.processing is None:
            return

        try:
            await deliver_cut(self.ctx, self.job, self.processing, is_gif=self.is_gif)
        finally:
            cut_guard.release(self.user_id)

    async def on_error(self, exc: Exception) -> None:
        if not isinstance(exc, CommandArgsError):
            raise exc

        field = exc.problems[0].field if exc.problems else ""
        line = {"start": self.start_error, "end": self.end_error}.get(field, self.usage)
        await self.ctx.message.answer(self.ctx.text(line))
