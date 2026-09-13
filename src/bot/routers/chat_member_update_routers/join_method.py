from aiogram.types import ChatMemberUpdated


def resolve_join_method(event: ChatMemberUpdated) -> str:
    """Как именно новый участник оказался в чате - см. поля
    `ChatMemberUpdated` (Bot API): `from_user` - кто СОВЕРШИЛ действие (не
    обязательно сам вступающий), `invite_link`/`via_join_request`/
    `via_chat_folder_invite_link` - разные способы входа по приглашению.

    Порядок проверок важен: "added_by_admin" проверяется первым и
    перекрывает остальные ветки - если действие совершил не сам
    вступающий, его именно ДОБАВИЛИ, остальные поля роли не играют.
    Дальше - folder-приглашение перед обычным invite_link (по докам Bot
    API оба поля описывают вход по ссылке, folder - более специфичный
    сигнал; точный порядок их совместного появления не проверялся вживую
    на реальном Telegram, только по документации полей)."""

    if event.new_chat_member.user.id != event.from_user.id:
        return "added_by_admin"

    if event.via_chat_folder_invite_link:
        return "chat_folder_invite_link"

    if event.invite_link is not None:
        return "invite_link"

    if event.via_join_request:
        return "join_request"

    return "self"


__all__ = ["resolve_join_method"]
