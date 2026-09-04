import asyncio
from pathlib import Path

import asyncpg

from app.adapters.repositories.postgres.documento_repository import DocumentoRepositoryPostgres
from app.config.settings import get_settings
from app.orchestration.gateway.model_gateway import ModelGateway

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


async def ingerir() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    gateway = ModelGateway(settings)
    repositorio = DocumentoRepositoryPostgres(pool)

    try:
        for pasta_tenant in sorted(DOCS_DIR.iterdir()):
            if not pasta_tenant.is_dir():
                continue
            tenant_id = pasta_tenant.name
            for arquivo in sorted(pasta_tenant.glob("*.md")):
                conteudo = arquivo.read_text(encoding="utf-8").strip()
                titulo = conteudo.splitlines()[0].lstrip("# ").strip()
                embedding = await gateway.embed(conteudo)
                await repositorio.inserir(
                    tenant_id=tenant_id,
                    titulo=titulo,
                    conteudo=conteudo,
                    embedding=embedding,
                )
                print(f"[{tenant_id}] {titulo} — ingerido")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(ingerir())
