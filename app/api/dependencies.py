from typing import Annotated

from fastapi import Header, HTTPException, status


async def obter_tenant_id(x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None) -> str:
    """Isola cada requisição por tenant; sem o header, não há como saber de quem são os dados."""
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header X-Tenant-Id é obrigatório",
        )
    return x_tenant_id
