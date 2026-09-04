from typing import Any

from app.adapters.repositories.contracts.documento_repository_interface import (
    DocumentoRepositoryInterface,
)
from app.adapters.tools.ferramenta import Ferramenta
from app.domain.guardrails.sanitizacao import sanitizar_conteudo_externo
from app.orchestration.gateway.model_gateway import ModelGateway

SCHEMA = {
    "type": "function",
    "function": {
        "name": "buscar_documentos",
        "description": (
            "Busca trechos da base de conhecimento interna (politicas de frete, devolucao, "
            "garantia, pagamento) relevantes para a pergunta do cliente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Termos de busca extraidos da pergunta do cliente.",
                },
            },
            "required": ["consulta"],
        },
    },
}


def criar_ferramenta_buscar_documentos(
    *,
    tenant_id: str,
    repositorio: DocumentoRepositoryInterface,
    gateway: ModelGateway,
    top_k: int,
) -> Ferramenta:
    """Isola a busca por tenant na origem — o modelo só escolhe os termos, nunca o tenant."""

    async def executar(argumentos: dict[str, Any]) -> str:
        embedding_consulta = await gateway.embed(argumentos["consulta"])
        documentos = await repositorio.buscar_similares(
            tenant_id=tenant_id,
            embedding_consulta=embedding_consulta,
            limite=top_k,
        )
        if not documentos:
            return "Nenhum documento relevante encontrado."
        texto = "\n\n".join(f"[{doc.titulo}]\n{doc.conteudo}" for doc in documentos)
        return sanitizar_conteudo_externo(texto)

    return Ferramenta(schema=SCHEMA, executar=executar)
