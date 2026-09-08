from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.adapters.repositories.contracts.tenant_repository_interface import (
    TenantRepositoryInterface,
)
from app.adapters.repositories.postgres.tenant_repository import get_tenant_repository


async def obter_tenant_id(
    request: Request,
    tenant_repositorio: Annotated[TenantRepositoryInterface, Depends(get_tenant_repository)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """O tenant vem da chave de API cadastrada no banco, nunca de um valor que o cliente declara."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization: Bearer <chave de API> é obrigatório",
        )
    chave = authorization.removeprefix("Bearer ").strip()
    autenticado = await tenant_repositorio.autenticar_por_chave(chave_api=chave)
    if autenticado is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida",
        )
    # O rate limiter (app/api/limiter.py) e a rota de chat leem daqui — evita repetir a consulta.
    request.state.tenant_id = autenticado.tenant_id
    request.state.modelo_override = autenticado.modelo_override
    return autenticado.tenant_id
