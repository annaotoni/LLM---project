from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: só confirma que o processo está de pé, sem depender de nada externo."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    """Readiness: só fica pronto quando consegue de fato conversar com o banco."""
    try:
        conexao = await asyncpg.connect(dsn=settings.database_url, timeout=2)
        await conexao.close()
    except (OSError, asyncpg.PostgresError) as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        ) from erro
    return {"status": "ready"}
