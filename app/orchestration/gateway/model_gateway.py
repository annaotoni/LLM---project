import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

import litellm
from fastapi import Depends

from app.config.settings import Settings, get_settings

logger = logging.getLogger("orchestration.gateway")


class ModelGateway:
    """Único ponto de contato com provedores de LLM — nenhum SDK de provider é usado fora daqui."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _api_base(self) -> str | None:
        """api_base só é necessário para Ollama; providers hospedados usam o endpoint canônico do litellm."""
        return self._settings.ollama_base_url if self._settings.llm_provider == "ollama" else None

    async def stream_completion(
        self,
        *,
        mensagens: list[dict[str, str]],
        tenant_id: str,
        prompt_id: str,
    ) -> AsyncIterator[str]:
        inicio = time.monotonic()
        resposta = await litellm.acompletion(
            model=self._settings.llm_model,
            messages=mensagens,
            api_base=self._api_base(),
            stream=True,
        )
        async for pedaco in resposta:
            delta = pedaco.choices[0].delta.content
            if delta:
                yield delta

        self._registrar_chamada(tenant_id=tenant_id, prompt_id=prompt_id, inicio=inicio)

    async def complete_with_tools(
        self,
        *,
        mensagens: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tenant_id: str,
        prompt_id: str,
    ) -> Any:
        """Completions sem streaming, usada pelo agente — precisa da resposta inteira para ler tool_calls."""
        inicio = time.monotonic()
        resposta = await litellm.acompletion(
            model=self._settings.llm_model,
            messages=mensagens,
            tools=tools,
            api_base=self._api_base(),
            stream=False,
        )
        self._registrar_chamada(
            tenant_id=tenant_id,
            prompt_id=prompt_id,
            inicio=inicio,
            resposta=resposta,
        )
        return resposta.choices[0].message

    async def embed(self, texto: str) -> list[float]:
        resposta = await litellm.aembedding(
            model=self._settings.llm_embedding_model,
            input=[texto],
            api_base=self._api_base(),
        )
        return resposta.data[0]["embedding"]

    def _registrar_chamada(
        self,
        *,
        tenant_id: str,
        prompt_id: str,
        inicio: float,
        resposta: Any = None,
    ) -> None:
        custo = None
        tokens_entrada = None
        tokens_saida = None
        if resposta is not None:
            uso = getattr(resposta, "usage", None)
            if uso is not None:
                tokens_entrada = uso.prompt_tokens
                tokens_saida = uso.completion_tokens
            try:
                custo = litellm.completion_cost(completion_response=resposta)
            except Exception:  # noqa: BLE001 — custo é best-effort; nunca deve derrubar a resposta.
                custo = None

        logger.info(
            "chamada_modelo concluída",
            extra={
                "tenant_id": tenant_id,
                "prompt_id": prompt_id,
                "model": self._settings.llm_model,
                "latencia_segundos": round(time.monotonic() - inicio, 3),
                "custo_usd": custo,
                "tokens_entrada": tokens_entrada,
                "tokens_saida": tokens_saida,
            },
        )


def get_model_gateway(settings: Annotated[Settings, Depends(get_settings)]) -> ModelGateway:
    return ModelGateway(settings)
