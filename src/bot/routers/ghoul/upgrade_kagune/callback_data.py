from selfrot import CallbackPayload


class KaguneUpgradePress(CallbackPayload, prefix="kagune_upgrade"):
    invoker_id: int
    name_english: str
