import logging
import os
import sys

from selfrot import BaseDispatcher
from selfrot.types import Update

from src.bot.services.dialog import DialogService

from .context import AppContext
from .routers import RootRouter


class Dispatcher(BaseDispatcher[AppContext]):
    routers = (RootRouter,)
    context = AppContext

    def __init__(self, token: str | None = None) -> None:
        super().__init__(token)
        self.dialog_service = DialogService()

    def create_context(self, update: Update) -> AppContext:
        return self.context(update, self.api, self.dialog_service)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # Отдельная переменная, а не BOT_TOKEN из .env: порт нельзя случайно запустить
    # на токене прод-бота.
    token = os.environ.get("SELFROT_BOT_TOKEN")
    if not token:
        sys.exit("Задайте SELFROT_BOT_TOKEN (токен dev-бота, не прод)")

    Dispatcher(token=token).start_polling()


if __name__ == "__main__":
    main()
