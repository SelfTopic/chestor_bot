from pathlib import Path

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError, ContextError
from selfrot.filter import Command, HasReplyToMessage, HasUser
from selfrot.types import InputFile

from src.bot.dialogs import Dialogs, Line
from src.bot.services.media import CollectionParser
from src.bot.types import MediaDownloadType
from src.bot.types.insert import MediaInsert

from ...context import AppContext
from ...services.media_paths import EXTENSION, collection_folder
from ..types import TextUserReplyToMessage

USAGE = Dialogs.admin.media.usage()


def phrase_params(text: str) -> dict[str, object]:
    pairs = (item.partition("=") for item in text.split())
    return {name: value for name, sep, value in pairs if sep and name}


class AddGifArgs(CommandArgs):
    target: str
    params: Rest = ""


class AddGifHandler(MessageHandler[AppContext[TextUserReplyToMessage]]):
    cmd = Command("add_gif", AddGifArgs)
    query = cmd & HasUser() & HasReplyToMessage()

    def folder(self, args: AddGifArgs, type_media: MediaDownloadType) -> Path | Line:
        if args.target in CollectionParser.MAP:
            return collection_folder(type_media, CollectionParser.parse(args.target))

        if not self.ctx.dialog_service.has_phrase(args.target):
            return Dialogs.admin.media.unknown_collection(
                collection=args.target, supported=", ".join(CollectionParser.MAP)
            )

        line = Line(args.target, phrase_params(args.params))
        try:
            return self.ctx.dialog_service.gifs(line).folder
        except KeyError as missing:
            return Dialogs.admin.media.missing_param(
                key=args.target, name=missing.args[0]
            )

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        message = self.ctx.message
        reply = message.reply_to_message

        if reply.video:
            type_media, file_id = MediaDownloadType.VIDEO, reply.video.file_id
        elif reply.animation:
            type_media, file_id = MediaDownloadType.ANIMATION, reply.animation.file_id
        else:
            await self.ctx.say(Dialogs.admin.media.no_media(), reply=True)
            return

        folder = self.folder(args, type_media)
        if isinstance(folder, Line):
            await self.ctx.say(folder, reply=True)
            return

        destination = folder / f"{type_media.value}_{file_id}{EXTENSION[type_media]}"
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            path = await self.ctx.download(destination)
        except ContextError:
            await self.ctx.say(USAGE, reply=True)
            return

        if await self.ctx.media_repository.exists_by_path(str(path)):
            await self.ctx.say(Dialogs.admin.media.exists(), reply=True)
            return

        is_phrase = args.target not in CollectionParser.MAP
        stored_type = MediaDownloadType.ANIMATION if is_phrase else type_media
        # file_id видео не годится для sendAnimation: фраза получит свой id при первой отправке.
        cached_id = file_id if stored_type == type_media else None
        await self.ctx.media_repository.insert(
            MediaInsert(
                media_type=stored_type.value,
                telegram_file_id=cached_id,
                collection=args.target,
                path=str(path),
                uploaded_by=message.user.id,
            )
        )

        caption = self.ctx.text(Dialogs.admin.media.saved(path=path))
        if type_media == MediaDownloadType.VIDEO:
            await message.answer_video(video=InputFile.from_path(path), caption=caption)
        else:
            await message.answer_animation(
                animation=InputFile.from_path(path), caption=caption
            )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(USAGE, reply=True)
            return

        raise exc


class MediaRouter(BaseRouter[AppContext]):
    handlers = (AddGifHandler,)
