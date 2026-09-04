from typing import Protocol

from app.domain.entities.documento import DocumentoRecuperado


class DocumentoRepositoryInterface(Protocol):
    async def buscar_similares(
        self,
        *,
        tenant_id: str,
        embedding_consulta: list[float],
        limite: int,
    ) -> list[DocumentoRecuperado]: ...

    async def inserir(
        self,
        *,
        tenant_id: str,
        titulo: str,
        conteudo: str,
        embedding: list[float],
    ) -> None: ...
