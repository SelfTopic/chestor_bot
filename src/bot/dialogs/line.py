from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Line:
    key: str
    params: dict[str, object] = field(default_factory=dict)


LineText = Callable[[Line], str]
