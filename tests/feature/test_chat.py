from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.adapters.repositories.postgres.documento_repository import get_documento_repository
from app.adapters.repositories.postgres.pedido_repository import get_pedido_repository
from app.api.main import app
from app.orchestration.gateway.model_gateway import get_model_gateway


class MensagemSemFerramenta:
    tool_calls = None
    content = "resposta direta, sem ferramenta"


class GatewayFalso:
    async def complete_with_tools(self, *, mensagens, tools, tenant_id, prompt_id):
        return MensagemSemFerramenta()

    async def stream_completion(self, *, mensagens, tenant_id, prompt_id) -> AsyncIterator[str]:
        for pedaco in ["Olá", ", ", "tudo bem?"]:
            yield pedaco


class DocumentoRepositorioFalso:
    async def buscar_similares(self, *, tenant_id, embedding_consulta, limite):
        return []

    async def inserir(self, *, tenant_id, titulo, conteudo, embedding):
        return None


class PedidoRepositorioFalso:
    async def buscar_por_numero(self, *, tenant_id, numero_pedido):
        return None


@pytest.fixture(autouse=True)
def dependencias_falsas():
    app.dependency_overrides[get_model_gateway] = lambda: GatewayFalso()
    app.dependency_overrides[get_documento_repository] = lambda: DocumentoRepositorioFalso()
    app.dependency_overrides[get_pedido_repository] = lambda: PedidoRepositorioFalso()
    yield
    app.dependency_overrides.clear()


def test_chat_exige_tenant_id() -> None:
    cliente = TestClient(app)

    resposta = cliente.post("/chat", json={"mensagem": "oi"})

    assert resposta.status_code == 400


def test_chat_faz_streaming_da_resposta() -> None:
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers={"X-Tenant-Id": "loja-azul"},
    )

    assert resposta.status_code == 200
    assert "Olá" in resposta.text
    assert "[DONE]" in resposta.text


def test_chat_rejeita_mensagem_vazia() -> None:
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": ""},
        headers={"X-Tenant-Id": "loja-azul"},
    )

    assert resposta.status_code == 422


def test_chat_nao_loga_pii_crua_do_usuario(caplog: pytest.LogCaptureFixture) -> None:
    cliente = TestClient(app)

    with caplog.at_level("INFO", logger="api.chat"):
        cliente.post(
            "/chat",
            json={"mensagem": "meu e-mail é cliente@exemplo.com, oi"},
            headers={"X-Tenant-Id": "loja-azul"},
        )

    registros = [r for r in caplog.records if r.name == "api.chat"]
    assert registros
    assert "cliente@exemplo.com" not in registros[0].mensagem_usuario
    assert "[E-MAIL OCULTADO]" in registros[0].mensagem_usuario
