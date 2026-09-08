import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
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
from app.api.limiter import limiter
from app.config.settings import Settings, get_settings
from app.domain.dto.chat import MensagemChatEntrada
from app.domain.guardrails.pii import mascarar_pii, mascarar_stream_pii
from app.orchestration.agent.graph import GRAFO
from app.orchestration.context.builder import construir_contexto
from app.orchestration.gateway.model_gateway import ModelGateway, get_model_gateway

logger = logging.getLogger("api.chat")

router = APIRouter(tags=["chat"])

_INSTRUCAO_SEM_FERRAMENTA = {
    "role": "user",
    "content": (
        "Você não tem mais tentativas de usar ferramentas. Responda diretamente, em texto, "
        "com o que você já sabe — não tente chamar nenhuma função."
    ),
}


async def _pronta(texto: str) -> AsyncIterator[str]:
    yield texto


def _mensagens_para_fallback(mensagens: list[dict]) -> list[dict]:
    """Prepara o histórico para uma resposta em texto puro após o corte de MAX_ITERACOES.

    A última mensagem pode ser uma tentativa de tool call que o grafo nunca chegou a executar
    (o corte aconteceu antes) — descartá-la evita que o modelo tente "completar" essa chamada
    como texto solto em vez de responder normalmente.
    """
    if mensagens and mensagens[-1].get("role") == "assistant" and mensagens[-1].get("tool_calls"):
        mensagens = mensagens[:-1]
    return [*mensagens, _INSTRUCAO_SEM_FERRAMENTA]


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(
    request: Request,
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
    # Definido em obter_tenant_id a partir de tenants.modelo_override — None usa o LLM_MODEL global.
    # Preparado para um futuro modelo fine-tunado por loja; nenhum treino acontece aqui.
    modelo_override: str | None = getattr(request.state, "modelo_override", None)
    ferramentas = [
        criar_ferramenta_buscar_documentos(
            tenant_id=tenant_id,
            repositorio=documento_repositorio,
            gateway=gateway,
            top_k=settings.rag_top_k,
        ),
        criar_ferramenta_consultar_pedido(tenant_id=tenant_id, repositorio=pedido_repositorio),
    ]

    resultado = await GRAFO.ainvoke(
        {
            "mensagens": contexto.mensagens,
            "tenant_id": tenant_id,
            "prompt_id": contexto.prompt_id,
            "iteracoes": 0,
            "precisa_ferramenta": False,
            "gateway": gateway,
            "ferramentas": ferramentas,
            "modelo": modelo_override,
        }
    )

    async def eventos() -> AsyncIterator[str]:
        resposta_final = resultado.get("resposta_final")
        if resposta_final is not None:
            resposta_bruta = _pronta(resposta_final)
        else:
            # Corte de segurança do MAX_ITERACOES sem o modelo ter fechado a resposta —
            # único caso em que ainda vale gerar a resposta final separadamente.
            resposta_bruta = gateway.stream_completion(
                mensagens=_mensagens_para_fallback(resultado["mensagens"]),
                tenant_id=tenant_id,
                prompt_id=contexto.prompt_id,
                modelo=modelo_override,
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
