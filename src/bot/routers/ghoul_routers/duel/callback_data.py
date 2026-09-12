"""Формат callback_data кнопок дуэли и его разбор - вынесено в чистую
функцию специально ради юнит-теста, тот же приём, что
`parse_kagune_callback_payload` в `upgrade_kagune.py` (единственное, что
защищает кнопку от нажатия не тем участником)."""

from typing import Optional, Tuple

VALID_ACTIONS = {
    "consent_initiator",
    "consent_target",
    "fora_serious",
    "fora_handicap",
    "outcome_rob",
    "outcome_release",
    "outcome_eat",
}


def parse_duel_callback_payload(payload: str) -> Optional[Tuple[int, str, int]]:
    """Разбирает "duel:<duel_id>:<action>:<expected_telegram_id>" ->
    (duel_id, action, expected_telegram_id), или None при любом
    несоответствии формата."""

    parts = payload.split(":")
    if len(parts) != 4 or parts[0] != "duel":
        return None

    _, duel_id_str, action, expected_id_str = parts
    if not duel_id_str.isdigit() or not expected_id_str.isdigit():
        return None
    if action not in VALID_ACTIONS:
        return None

    return int(duel_id_str), action, int(expected_id_str)


__all__ = ["parse_duel_callback_payload", "VALID_ACTIONS"]
