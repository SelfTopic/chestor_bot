import asyncio
import logging
from pathlib import Path

from selfrot.types import InputFile, Message

from src.bot.dialogs import Dialogs
from src.bot.types import VideoCutJob

from ....context import AppContext
from ...types import TextMessage

logger = logging.getLogger(__name__)


async def deliver_cut(
    ctx: AppContext[TextMessage], job: VideoCutJob, processing: Message, *, is_gif: bool
) -> None:
    message = ctx.message

    try:
        await ctx.video_worker.enqueue(job)

        result_path = await asyncio.wait_for(job.result, timeout=60.0)

        await processing.delete()

        if not is_gif:
            await message.reply_video(
                video=InputFile.from_path(result_path),
                caption=ctx.text(Dialogs.anime.video(caption=job.caption))
                if job.caption
                else "",
            )
        else:
            await message.reply_animation(
                animation=InputFile.from_path(result_path),
                caption=ctx.text(Dialogs.anime.gif(caption=job.caption))
                if job.caption
                else "",
            )

    except asyncio.TimeoutError:
        await processing.edit_text(ctx.text(Dialogs.anime.timeout()))
        job.cancel()

    except asyncio.CancelledError:
        await processing.edit_text(ctx.text(Dialogs.anime.cancelled()))

    except asyncio.QueueFull:
        await processing.edit_text(ctx.text(Dialogs.anime.queue_full()))

    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        await processing.edit_text(ctx.text(Dialogs.anime.failed(error=str(e))))

    finally:
        if Path(job.output_file_path).exists():
            try:
                Path(job.output_file_path).unlink(missing_ok=True)
                logger.debug(f"Cleaned up temp file: {job.output_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")
