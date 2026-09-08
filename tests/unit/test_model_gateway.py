from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config.settings import Settings
from app.orchestration.gateway.model_gateway import ModelGateway


def _settings(provider: str = "ollama") -> Settings:
    return Settings(
        database_url="postgresql://teste:teste@localhost/teste",
        llm_provider=provider,
        llm_model="ollama/qwen2.5:3b" if provider == "ollama" else "gpt-4o",
        llm_embedding_model="ollama/all-minilm",
        ollama_base_url="http://localhost:11434",
        rag_top_k=3,
    )


def test_api_base_retorna_url_ollama_para_provider_ollama() -> None:
    gateway = ModelGateway(_settings("ollama"))
    assert gateway._api_base() == "http://localhost:11434"


def test_api_base_retorna_none_para_provider_openai() -> None:
    gateway = ModelGateway(_settings("openai"))
    assert gateway._api_base() is None


@pytest.mark.asyncio
async def test_stream_completion_passa_api_base_apenas_para_ollama() -> None:
    gateway = ModelGateway(_settings("ollama"))

    pedaco_1 = MagicMock()
    pedaco_1.choices = [MagicMock()]
    pedaco_1.choices[0].delta.content = "oi"

    pedaco_2 = MagicMock()
    pedaco_2.choices = [MagicMock()]
    pedaco_2.choices[0].delta.content = None

    async def _iter_pedacos():
        yield pedaco_1
        yield pedaco_2

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = _iter_pedacos()
        _ = [p async for p in gateway.stream_completion(
            mensagens=[{"role": "user", "content": "oi"}],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
        )]

    chamada_kwargs = mock_litellm.call_args.kwargs
    assert chamada_kwargs.get("api_base") == "http://localhost:11434"


@pytest.mark.asyncio
async def test_stream_completion_nao_passa_api_base_para_openai() -> None:
    gateway = ModelGateway(_settings("openai"))

    pedaco = MagicMock()
    pedaco.choices = [MagicMock()]
    pedaco.choices[0].delta.content = "oi"

    async def _iter_pedaco():
        yield pedaco

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = _iter_pedaco()
        _ = [p async for p in gateway.stream_completion(
            mensagens=[{"role": "user", "content": "oi"}],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
        )]

    chamada_kwargs = mock_litellm.call_args.kwargs
    assert chamada_kwargs.get("api_base") is None


@pytest.mark.asyncio
async def test_stream_completion_marca_tenant_id_como_metadata() -> None:
    gateway = ModelGateway(_settings("ollama"))

    pedaco = MagicMock()
    pedaco.choices = [MagicMock()]
    pedaco.choices[0].delta.content = "oi"

    async def _iter_pedaco():
        yield pedaco

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = _iter_pedaco()
        _ = [p async for p in gateway.stream_completion(
            mensagens=[{"role": "user", "content": "oi"}],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
        )]

    chamada_kwargs = mock_litellm.call_args.kwargs
    assert chamada_kwargs["metadata"] == {"tenant_id": "loja-azul", "prompt_id": "chat.agente@v1"}


@pytest.mark.asyncio
async def test_stream_completion_usa_llm_model_global_sem_override() -> None:
    gateway = ModelGateway(_settings("ollama"))

    pedaco = MagicMock()
    pedaco.choices = [MagicMock()]
    pedaco.choices[0].delta.content = "oi"

    async def _iter_pedaco():
        yield pedaco

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = _iter_pedaco()
        _ = [p async for p in gateway.stream_completion(
            mensagens=[{"role": "user", "content": "oi"}],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
        )]

    assert mock_litellm.call_args.kwargs["model"] == "ollama/qwen2.5:3b"


@pytest.mark.asyncio
async def test_stream_completion_usa_modelo_override_do_tenant_quando_informado() -> None:
    gateway = ModelGateway(_settings("ollama"))

    pedaco = MagicMock()
    pedaco.choices = [MagicMock()]
    pedaco.choices[0].delta.content = "oi"

    async def _iter_pedaco():
        yield pedaco

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = _iter_pedaco()
        _ = [p async for p in gateway.stream_completion(
            mensagens=[{"role": "user", "content": "oi"}],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
            modelo="ollama_chat/qwen2.5:3b-loja-azul",
        )]

    assert mock_litellm.call_args.kwargs["model"] == "ollama_chat/qwen2.5:3b-loja-azul"


@pytest.mark.asyncio
async def test_complete_with_tools_usa_modelo_override_do_tenant_quando_informado() -> None:
    gateway = ModelGateway(_settings("ollama"))

    resposta_falsa = MagicMock()
    resposta_falsa.choices = [MagicMock()]
    resposta_falsa.choices[0].message = MagicMock()
    resposta_falsa.usage = None

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = resposta_falsa
        await gateway.complete_with_tools(
            mensagens=[{"role": "user", "content": "oi"}],
            tools=[],
            tenant_id="loja-azul",
            prompt_id="chat.agente@v1",
            modelo="ollama_chat/qwen2.5:3b-loja-azul",
        )

    chamada_kwargs = mock_litellm.call_args.kwargs
    assert chamada_kwargs["model"] == "ollama_chat/qwen2.5:3b-loja-azul"
    assert chamada_kwargs["metadata"] == {"tenant_id": "loja-azul", "prompt_id": "chat.agente@v1"}


@pytest.mark.asyncio
async def test_embed_marca_tenant_id_como_metadata() -> None:
    gateway = ModelGateway(_settings("ollama"))

    resposta_falsa = MagicMock()
    resposta_falsa.data = [{"embedding": [0.1, 0.2]}]

    with patch("litellm.aembedding", new_callable=AsyncMock) as mock_litellm:
        mock_litellm.return_value = resposta_falsa
        embedding = await gateway.embed("texto de teste", tenant_id="loja-azul")

    assert embedding == [0.1, 0.2]
    assert mock_litellm.call_args.kwargs["metadata"] == {"tenant_id": "loja-azul"}
