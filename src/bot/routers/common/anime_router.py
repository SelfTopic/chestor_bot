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
    command = message.text

    if not command:
        raise ValueError("Command text is empty")

    args = command.split()

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
        f"src/bot/assets/video/tokio_ghoul/Season_{season}_Episode_{episode}.mp4"
    )

    if not input_path.exists():
        await message.answer("Такого видео не найдено.")
        return

    # Полная серия
    if len(args) == 3:
        await message.reply_video(
            FSInputFile(input_path),
            caption=(f"Сезон {season}. Серия {episode}"),
        )
        return

    # Отрывок
    if len(args) != 5:
        await message.answer(
            "Неверный формат команды.\n\nПример:\n/anime 1 12 18:37 18:47"
        )
        return

    start_time = args[3]
    end_time = args[4]

    if not video_cutter.validate_time_format(start_time):
        await message.answer("Неверный начальный таймкод.\n\nПример: 18:37")
        return

    if not video_cutter.validate_time_format(end_time):
        await message.answer("Неверный конечный таймкод.\n\nПример: 18:47")
        return

    output_path = video_cutter.generate_output_path(input_path.name)

    job = VideoCutJob(
        input_file_path=input_path,
        output_file_path=output_path,
        start_time=start_time,
        end_time=end_time,
    )

    await video_worker.enqueue(job)

    try:
        await job.result

        await message.reply_video(
            FSInputFile(job.output_file_path),
            caption=(
                f"Сезон {season}. Серия {episode}. Отрывок с {start_time} до {end_time}"
            ),
        )

    except Exception:
        logger.exception(
            "Failed to process video: %s",
            job.output_file_path,
        )

        await message.answer("Произошла ошибка во время обработки видео.")

    finally:
        Path(job.output_file_path).unlink(missing_ok=True)
