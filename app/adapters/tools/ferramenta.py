from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Ferramenta:
    schema: dict[str, Any]
    executar: Callable[[dict[str, Any]], Awaitable[str]]

    @property
    def nome(self) -> str:
        return self.schema["function"]["name"]
