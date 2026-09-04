from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Pedido:
    numero_pedido: str
    status: str
    previsao_entrega: date | None
    cliente_nome: str
