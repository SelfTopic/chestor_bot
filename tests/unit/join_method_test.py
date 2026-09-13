from types import SimpleNamespace

from src.bot.routers.chat_member_update_routers.join_method import resolve_join_method


def _make_event(
    *,
    actor_id: int = 1,
    joined_user_id: int = 1,
    invite_link: object | None = None,
    via_join_request: bool | None = None,
    via_chat_folder_invite_link: bool | None = None,
):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=actor_id),
        new_chat_member=SimpleNamespace(user=SimpleNamespace(id=joined_user_id)),
        invite_link=invite_link,
        via_join_request=via_join_request,
        via_chat_folder_invite_link=via_chat_folder_invite_link,
    )


def test_self_join_with_no_extra_signals_is_self():
    event = _make_event(actor_id=1, joined_user_id=1)
    assert resolve_join_method(event) == "self"


def test_added_by_someone_else_takes_priority_over_everything():
    """Если действие совершил не сам вступающий - его добавили, остальные
    поля (даже если бы они были True) роли не играют."""

    event = _make_event(
        actor_id=999,
        joined_user_id=1,
        invite_link=object(),
        via_join_request=True,
        via_chat_folder_invite_link=True,
    )
    assert resolve_join_method(event) == "added_by_admin"


def test_joined_via_invite_link():
    event = _make_event(actor_id=1, joined_user_id=1, invite_link=object())
    assert resolve_join_method(event) == "invite_link"


def test_joined_via_join_request():
    event = _make_event(actor_id=1, joined_user_id=1, via_join_request=True)
    assert resolve_join_method(event) == "join_request"


def test_joined_via_chat_folder_invite_link():
    event = _make_event(actor_id=1, joined_user_id=1, via_chat_folder_invite_link=True)
    assert resolve_join_method(event) == "chat_folder_invite_link"


def test_chat_folder_invite_link_takes_priority_over_plain_invite_link():
    event = _make_event(
        actor_id=1,
        joined_user_id=1,
        invite_link=object(),
        via_chat_folder_invite_link=True,
    )
    assert resolve_join_method(event) == "chat_folder_invite_link"
