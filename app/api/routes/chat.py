import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.adapters.repositories.contracts.documento_repository_interface import (
    DocumentoRepositoryInterface,
)
from app.adapters.repositories.contracts.pedido_repository_interface import (
    PedidoRepositoryInterface,
)
from app.adapters.repositories.postgres.documento_repository import get_documento_repository
from app.adapters.repositories.postgres.pedido_repository import get_pedido_repository
from app.adapters.tools.buscar_documentos import criar_ferramenta_buscar_documentos
from app.adapters.tools.consultar_pedido import criar_ferramenta_consultar_pedido
from app.api.dependencies import obter_tenant_id
from app.config.settings import Settings, get_settings
from app.domain.dto.chat import MensagemChatEntrada
from app.domain.guardrails.pii import mascarar_pii, mascarar_stream_pii
from app.orchestration.agent.graph import construir_grafo
from app.orchestration.context.builder import construir_contexto
from app.orchestration.gateway.model_gateway import ModelGateway, get_model_gateway

logger = logging.getLogger("api.chat")

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    entrada: MensagemChatEntrada,
    tenant_id: Annotated[str, Depends(obter_tenant_id)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
    documento_repositorio: Annotated[
        DocumentoRepositoryInterface, Depends(get_documento_repository)
    ],
    pedido_repositorio: Annotated[PedidoRepositoryInterface, Depends(get_pedido_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    contexto = construir_contexto(entrada.mensagem)
    ferramentas = [
        criar_ferramenta_buscar_documentos(
            tenant_id=tenant_id,
            repositorio=documento_repositorio,
            gateway=gateway,
            top_k=settings.rag_top_k,
        ),
        criar_ferramenta_consultar_pedido(tenant_id=tenant_id, repositorio=pedido_repositorio),
    ]

    grafo = construir_grafo(gateway, ferramentas)
    resultado = await grafo.ainvoke(
        {
            "mensagens": contexto.mensagens,
            "tenant_id": tenant_id,
            "prompt_id": contexto.prompt_id,
            "iteracoes": 0,
            "precisa_ferramenta": False,
        }
    )

    async def eventos() -> AsyncIterator[str]:
        resposta_bruta = gateway.stream_completion(
            mensagens=resultado["mensagens"],
            tenant_id=tenant_id,
            prompt_id=contexto.prompt_id,
        )
        partes_resposta: list[str] = []
        async for pedaco in mascarar_stream_pii(resposta_bruta):
            partes_resposta.append(pedaco)
            yield f"data: {pedaco}\n\n"
        yield "data: [DONE]\n\n"

        logger.info(
            "interacao_chat concluída",
            extra={
                "tenant_id": tenant_id,
                "prompt_id": contexto.prompt_id,
                "mensagem_usuario": mascarar_pii(entrada.mensagem),
                "resposta": mascarar_pii("".join(partes_resposta)),
            },
        )

    return StreamingResponse(eventos(), media_type="text/event-stream")
