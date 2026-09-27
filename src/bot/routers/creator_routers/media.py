from pathlib import Path

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError, ContextError
from selfrot.filter import Command, HasReplyToMessage, HasUser
from selfrot.types import InputFile

from src.bot.dialogs import Dialogs
from src.bot.exceptions import CollectionNotFoundError
from src.bot.services.media import CollectionParser
from src.bot.types import MediaCollection, MediaDownloadType
from src.bot.types.insert import MediaInsert

from ...context import AppContext
from ...services.media_paths import EXTENSION, collection_folder
from ..types import TextUserReplyToMessage

USAGE = Dialogs.admin.media.usage()


def target_path(
    type_media: MediaDownloadType,
    collection: MediaCollection,
    file_id: str,
) -> Path:
    return (
        collection_folder(type_media, collection)
        / f"{type_media.value}_{file_id}{EXTENSION[type_media]}"
    )


class AddGifArgs(CommandArgs):
    collection: Rest


class AddGifHandler(MessageHandler[AppContext[TextUserReplyToMessage]]):
    cmd = Command("add_gif", AddGifArgs)
    query = cmd & HasUser() & HasReplyToMessage()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        message = self.ctx.message
        reply = message.reply_to_message

        if reply.video:
            type_media, file_id = MediaDownloadType.VIDEO, reply.video.file_id
        elif reply.animation:
            type_media, file_id = MediaDownloadType.ANIMATION, reply.animation.file_id
        else:
            await message.reply(self.ctx.text(Dialogs.admin.media.no_media()))
            return

        try:
            collection = CollectionParser.parse(args.collection)
        except CollectionNotFoundError as e:
            unknown = Dialogs.admin.media.unknown_collection(
                collection=e.collection, supported=e.supported
            )
            await message.reply(self.ctx.text(unknown))
            return

        destination = target_path(type_media, collection, file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            path = await self.ctx.download(destination)
        except ContextError:
            await message.reply(self.ctx.text(USAGE))
            return

        if await self.ctx.media_repository.exists_by_path(str(path)):
            await message.reply(self.ctx.text(Dialogs.admin.media.exists()))
            return

        await self.ctx.media_repository.insert(
            MediaInsert(
                media_type=type_media.value,
                telegram_file_id=file_id,
                collection=collection.value,
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
            await self.ctx.message.reply(self.ctx.text(USAGE))
            return

        raise exc


class MediaRouter(BaseRouter[AppContext]):
    handlers = (AddGifHandler,)
