from typing import Protocol

from app.domain.entities.tenant import TenantAutenticado


class TenantRepositoryInterface(Protocol):
    async def autenticar_por_chave(self, *, chave_api: str) -> TenantAutenticado | None: ...
