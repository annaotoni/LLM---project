from typing import Protocol

from app.domain.entities.pedido import Pedido


class PedidoRepositoryInterface(Protocol):
    async def buscar_por_numero(self, *, tenant_id: str, numero_pedido: str) -> Pedido | None: ...
