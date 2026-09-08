"""
Eval de qualidade do RAG — não é teste unitário.

Precisa do Postgres+pgvector e do Ollama reais, de pé, com os documentos de exemplo já
ingeridos (docker compose up -d postgres ollama && python scripts/ingest_documents.py).
Roda separado da suíte padrão: pytest tests/evals -v -m eval
"""

import asyncpg
import pytest

from app.adapters.repositories.postgres.documento_repository import DocumentoRepositoryPostgres
from app.config.settings import get_settings
from app.orchestration.gateway.model_gateway import ModelGateway
from tests.evals.dataset_rag import CASOS

LIMIAR_RECALL = 0.7


@pytest.mark.eval
@pytest.mark.asyncio
async def test_recall_top_k_da_busca_rag() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    gateway = ModelGateway(settings)
    repositorio = DocumentoRepositoryPostgres(pool)

    acertos = 0
    linhas_relatorio = []
    try:
        for caso in CASOS:
            embedding = await gateway.embed(caso["pergunta"], tenant_id=caso["tenant_id"])
            resultados = await repositorio.buscar_similares(
                tenant_id=caso["tenant_id"], embedding_consulta=embedding, limite=3
            )
            titulos_recuperados = [documento.titulo for documento in resultados]
            acertou = caso["titulo_esperado"] in titulos_recuperados
            acertos += int(acertou)
            linhas_relatorio.append(
                f"{'OK    ' if acertou else 'FALHOU'} | pergunta={caso['pergunta']!r} "
                f"| esperado={caso['titulo_esperado']!r} | recuperado={titulos_recuperados}"
            )
    finally:
        await pool.close()

    recall = acertos / len(CASOS)
    relatorio = "\n".join(linhas_relatorio)
    assert recall >= LIMIAR_RECALL, (
        f"recall@3 = {recall:.2f}, abaixo do limiar {LIMIAR_RECALL}\n{relatorio}"
    )
