from typing import Annotated

import asyncpg
from fastapi import Depends

from app.adapters.database import obter_pool
from app.domain.entities.documento import DocumentoRecuperado


def _vetor_para_sql(embedding: list[float]) -> str:
    return "[" + ",".join(str(valor) for valor in embedding) + "]"


class DocumentoRepositoryPostgres:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def buscar_similares(
        self,
        *,
        tenant_id: str,
        embedding_consulta: list[float],
        limite: int,
    ) -> list[DocumentoRecuperado]:
        query = """
            SELECT titulo, conteudo, embedding <=> $2::vector AS distancia
            FROM documentos
            WHERE tenant_id = $1
            ORDER BY embedding <=> $2::vector
            LIMIT $3
        """
        linhas = await self._pool.fetch(
            query, tenant_id, _vetor_para_sql(embedding_consulta), limite
        )
        return [
            DocumentoRecuperado(
                titulo=linha["titulo"],
                conteudo=linha["conteudo"],
                distancia=linha["distancia"],
            )
            for linha in linhas
        ]

    async def inserir(
        self,
        *,
        tenant_id: str,
        titulo: str,
        conteudo: str,
        embedding: list[float],
    ) -> None:
        query = """
            INSERT INTO documentos (tenant_id, titulo, conteudo, embedding)
            VALUES ($1, $2, $3, $4::vector)
            ON CONFLICT (tenant_id, titulo) DO UPDATE
            SET conteudo = EXCLUDED.conteudo, embedding = EXCLUDED.embedding
        """
        await self._pool.execute(
            query, tenant_id, titulo, conteudo, _vetor_para_sql(embedding)
        )


def get_documento_repository(
    pool: Annotated[asyncpg.Pool, Depends(obter_pool)],
) -> DocumentoRepositoryPostgres:
    return DocumentoRepositoryPostgres(pool)
