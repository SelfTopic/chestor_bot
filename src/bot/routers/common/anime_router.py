import asyncio
import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...services import VideoCutterService, VideoWorker
from ...types import VideoCutJob

logger = logging.getLogger(__name__)
router = Router(name=__name__)


@router.message(Command("anime"))
@inject
async def anime_handler(
    message: Message,
    video_worker: VideoWorker = Provide[Container.video_worker],
    video_cutter: VideoCutterService = Provide[Container.video_cutter_service],
):
    if not message.text:
        await message.answer("Пожалуйста, укажите параметры команды.")
        return

    args = message.text.split()

    if len(args) < 3:
        await message.answer(
            "Укажи сезон и серию.\n\n"
            "Пример:\n"
            "/anime 1 1\n\n"
            "Также могу дать отрывок:\n"
            "/anime 1 12 18:37 18:47"
        )
        return

    season = args[1]
    episode = args[2]

    input_path = Path(
        f"src/assets/videos/tokio_ghoul/Season_{season}_Episode_{episode}.mp4"
    )

    if not input_path.exists():
        await message.answer(f"❌ Видео сезона {season} серии {episode} не найдено.")
        return

    if len(args) == 3:
        await message.reply_video(
            FSInputFile(input_path),
            caption=f"🎬 Сезон {season}. Серия {episode}",
        )
        return

    if len(args) < 5:
        await message.answer(
            "❌ Неверный формат команды.\n\n"
            "Пример для отрывка:\n"
            "/anime 1 12 18:37 18:47\n"
            "или\n"
            "/anime  12 18:37 18:47 gif\n"
            "чтобы получить отрывок сразу гифкой"
        )
        return

    start_time = args[3]
    end_time = args[4]

    is_gif = False
    if len(args) == 6 and args[5] == "gif":
        is_gif = True

    if not video_cutter.validate_time_format(start_time):
        await message.answer("❌ Неверный начальный таймкод.\n\nПример: 18:37")
        return

    if not video_cutter.validate_time_format(end_time):
        await message.answer("❌ Неверный конечный таймкод.\n\nПример: 18:47")
        return

    try:
        duration = video_cutter.parse_duration(start_time, end_time)
        if duration <= 0:
            raise ValueError

    except ValueError:
        await message.answer("❌ Конечный таймкод должен быть больше начального.")
        return

    output_path = video_cutter.generate_output_path(input_path.name, is_gif=is_gif)

    job = VideoCutJob(
        input_file_path=input_path,
        output_file_path=output_path,
        start_time=start_time,
        end_time=end_time,
        chat_id=message.chat.id,
        caption=f"🎬 Сезон {season}. Серия {episode}. Отрывок с {start_time} до {end_time}",
    )

    processing_msg = await message.reply(
        "⏳ Начинаю нарезку видео...\n"
        f"Сезон {season}, серия {episode}\n"
        f"Отрывок: {start_time} - {end_time}\n\n"
        "Это может занять несколько секунд."
    )

    try:
        await video_worker.enqueue(job)

        result_path = await asyncio.wait_for(job.result, timeout=60.0)

        await processing_msg.delete()

        if not is_gif:
            await message.reply_video(
                FSInputFile(result_path),
                caption="Video\n" + job.caption if job.caption else "",
            )
        else:
            await message.reply_animation(
                FSInputFile(result_path),
                caption="Gif\n" + job.caption if job.caption else "",
            )

    except asyncio.TimeoutError:
        await processing_msg.edit_text(
            "❌ Превышено время ожидания нарезки видео.\n"
            "Попробуйте выбрать меньший фрагмент или повторите позже."
        )
        job.cancel()

    except asyncio.CancelledError:
        await processing_msg.edit_text("❌ Нарезка видео была отменена.")

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при нарезке видео: {str(e)}"
        )

    finally:
        if Path(job.output_file_path).exists():
            try:
                Path(job.output_file_path).unlink(missing_ok=True)
                logger.debug(f"Cleaned up temp file: {job.output_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")
