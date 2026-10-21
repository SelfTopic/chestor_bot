import difflib
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
from ..types import TextUserMessage, TextUserReplyToMessage

USAGE = Dialogs.admin.media.usage()


NEW_VALUE_MARK = "!"


def phrase_params(text: str) -> dict[str, str]:
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
            return self.unknown_target(args.target)

        params = phrase_params(args.params)
        confirmed = {
            name for name, value in params.items() if value.endswith(NEW_VALUE_MARK)
        }
        line = Line(
            args.target,
            {
                name: value.removesuffix(NEW_VALUE_MARK)
                for name, value in params.items()
            },
        )
        try:
            gifs = self.ctx.dialog_service.gifs(line)
        except KeyError as missing:
            return Dialogs.admin.media.missing_param(
                key=args.target, name=missing.args[0]
            )

        name = gifs.varying
        if name is None or name in confirmed or gifs.folder.is_dir():
            return gifs.folder
        known = (
            sorted(path.name for path in gifs.folder.parent.iterdir() if path.is_dir())
            if gifs.folder.parent.is_dir()
            else []
        )
        return Dialogs.admin.media.unknown_value(
            key=args.target,
            name=name,
            value=line.params[name],
            known=", ".join(known) or "—",
        )

    def unknown_target(self, target: str) -> Line:
        keys = self.ctx.dialog_service.keys()
        section = [key for key in keys if key.startswith(f"{target}.")]
        if section:
            return Dialogs.admin.media.section(section=target, keys="\n".join(section))

        close = difflib.get_close_matches(target, [*keys, *CollectionParser.MAP], n=3)
        if close:
            return Dialogs.admin.media.did_you_mean(
                target=target, options=", ".join(close)
            )

        return Dialogs.admin.media.unknown_collection(
            collection=target, supported=", ".join(CollectionParser.MAP)
        )

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        message = self.ctx.message
        reply = message.reply_to_message

        if reply.video:
            type_media, file = MediaDownloadType.VIDEO, reply.video
        elif reply.animation:
            type_media, file = MediaDownloadType.ANIMATION, reply.animation
        else:
            await self.ctx.say(Dialogs.admin.media.no_media(), reply=True)
            return

        folder = self.folder(args, type_media)
        if isinstance(folder, Line):
            await self.ctx.say(folder, reply=True)
            return

        destination = (
            folder / f"{type_media.value}_{file.file_id}{EXTENSION[type_media]}"
        )
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
        # Видео, сохранённое для фразы, уходит как анимация — это другой файл Telegram:
        # его id запоминается после отправки ниже.
        same_file = stored_type == type_media
        await self.ctx.media_repository.insert(
            MediaInsert(
                media_type=stored_type.value,
                telegram_file_id=file.file_id if same_file else None,
                file_unique_id=file.file_unique_id if same_file else None,
                collection=args.target,
                path=str(path),
                uploaded_by=message.user.id,
            )
        )

        caption = self.ctx.text(Dialogs.admin.media.saved(path=path))
        if stored_type == MediaDownloadType.VIDEO:
            await message.answer_video(video=file.file_id, caption=caption)
            return

        sent = await message.answer_animation(
            animation=file.file_id if same_file else InputFile.from_path(path),
            caption=caption,
        )
        if not same_file and sent.animation is not None:
            await self.ctx.media_repository.update_file_id(
                path=str(path),
                new_file_id=sent.animation.file_id,
                file_unique_id=sent.animation.file_unique_id,
            )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(USAGE, reply=True)
            return

        raise exc


class RemoveGifHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Command("remove_gif") & HasUser()

    async def handle(self) -> None:
        reply = self.ctx.message.reply_to_message
        file = reply and (reply.animation or reply.video)
        if not file:
            await self.ctx.say(Dialogs.admin.media.remove_usage(), reply=True)
            return

        repository = self.ctx.media_repository
        found = await repository.find_by_file(file.file_unique_id, file.file_id)
        if not found:
            await self.ctx.say(Dialogs.admin.media.remove_not_found(), reply=True)
            return

        # Сначала файлы: если удалить не выйдет, записи в БД останутся и ничего не потеряется.
        for media in found:
            Path(media.path).unlink(missing_ok=True)
        await repository.delete_by_ids([media.id for media in found])

        paths = "\n".join(media.path for media in found)
        await self.ctx.say(Dialogs.admin.media.removed(paths=paths), reply=True)


class MediaRouter(BaseRouter[AppContext]):
    handlers = (AddGifHandler, RemoveGifHandler)
