class PromoError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class PromoNameTaken(PromoError): ...


class PromoNotFound(PromoError): ...


class PromoExpired(PromoError): ...


class PromoExhausted(PromoError): ...


class PromoAlreadyActivated(PromoError): ...
