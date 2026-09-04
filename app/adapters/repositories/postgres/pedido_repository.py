from typing import Annotated

import asyncpg
from fastapi import Depends

from app.adapters.database import obter_pool
from app.domain.entities.pedido import Pedido


class PedidoRepositoryPostgres:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def buscar_por_numero(self, *, tenant_id: str, numero_pedido: str) -> Pedido | None:
        query = """
            SELECT numero_pedido, status, previsao_entrega, cliente_nome
            FROM pedidos
            WHERE tenant_id = $1 AND numero_pedido = $2
        """
        linha = await self._pool.fetchrow(query, tenant_id, numero_pedido)
        if linha is None:
            return None
        return Pedido(
            numero_pedido=linha["numero_pedido"],
            status=linha["status"],
            previsao_entrega=linha["previsao_entrega"],
            cliente_nome=linha["cliente_nome"],
        )


def get_pedido_repository(
    pool: Annotated[asyncpg.Pool, Depends(obter_pool)],
) -> PedidoRepositoryPostgres:
    return PedidoRepositoryPostgres(pool)
