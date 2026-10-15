# От этих аккаунтов Telegram приходят сообщения, за которыми нет человека: автопересылки из
# привязанного канала, анонимные админы и сообщения от имени канала. Бот записывает их в
# users как обычных отправителей, поэтому деньги и браки отсекают их по id.
TELEGRAM = 777000
GROUP_ANONYMOUS_BOT = 1087968824
CHANNEL_BOT = 136817688

SERVICE_ACCOUNTS = frozenset({TELEGRAM, GROUP_ANONYMOUS_BOT, CHANNEL_BOT})


def is_service_account(telegram_id: int) -> bool:
    return telegram_id in SERVICE_ACCOUNTS
