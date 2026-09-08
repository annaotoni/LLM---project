import hashlib
from typing import Annotated

import asyncpg
from fastapi import Depends

from app.adapters.database import obter_pool
from app.domain.entities.tenant import TenantAutenticado


def hash_chave_api(chave_api: str) -> str:
    """Mesmo hash usado para popular e para consultar `tenants.chave_api_hash` — nunca a chave em texto puro."""
    return hashlib.sha256(chave_api.encode()).hexdigest()


class TenantRepositoryPostgres:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def autenticar_por_chave(self, *, chave_api: str) -> TenantAutenticado | None:
        query = "SELECT tenant_id, modelo_override FROM tenants WHERE chave_api_hash = $1"
        linha = await self._pool.fetchrow(query, hash_chave_api(chave_api))
        if linha is None:
            return None
        return TenantAutenticado(tenant_id=linha["tenant_id"], modelo_override=linha["modelo_override"])


def get_tenant_repository(
    pool: Annotated[asyncpg.Pool, Depends(obter_pool)],
) -> TenantRepositoryPostgres:
    return TenantRepositoryPostgres(pool)
