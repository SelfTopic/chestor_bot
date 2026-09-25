from selfrot import CallbackPayload


class KaguneUpgradePress(CallbackPayload, prefix="kagune_upgrade"):
    """invoker_id едет прямо в данных кнопки: в группе клавиатуру видят все, а
    нажать имеет право только тот, кто вызвал "растить кагуне" (проверка в
    handlers.py). Заменяет ручной parse_kagune_callback_payload(payload) у прода —
    формат и типы полей проверяет сама библиотека при unpack()."""

    invoker_id: int
    name_english: str
