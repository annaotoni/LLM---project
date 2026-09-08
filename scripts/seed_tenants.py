import asyncio

import asyncpg

from app.adapters.repositories.postgres.tenant_repository import hash_chave_api
from app.config.settings import get_settings

# Chaves de desenvolvimento local — gere chaves de verdade antes de expor a API publicamente.
# A chave em si nunca é persistida — só o hash (ver tenant_repository.hash_chave_api).
TENANTS = [
    ("loja-azul", "dev-loja-azul"),
    ("loja-verde", "dev-loja-verde"),
]


async def semear() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    try:
        for tenant_id, chave_api in TENANTS:
            await pool.execute(
                """
                INSERT INTO tenants (tenant_id, chave_api_hash)
                VALUES ($1, $2)
                ON CONFLICT (tenant_id) DO UPDATE SET chave_api_hash = EXCLUDED.chave_api_hash
                """,
                tenant_id,
                hash_chave_api(chave_api),
            )
            print(f"[{tenant_id}] chave de API — semeada (chave: {chave_api})")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(semear())
