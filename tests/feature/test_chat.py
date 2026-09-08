from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from app.adapters.repositories.postgres.documento_repository import get_documento_repository
from app.adapters.repositories.postgres.pedido_repository import get_pedido_repository
from app.adapters.repositories.postgres.tenant_repository import get_tenant_repository
from app.api.main import app
from app.domain.entities.tenant import TenantAutenticado
from app.orchestration.gateway.model_gateway import get_model_gateway

CHAVES_TESTE = {
    "loja-azul": "chave-azul-teste",
    "loja-teste-rate-limit-a": "chave-rate-a",
    "loja-teste-rate-limit-b": "chave-rate-b",
    "loja-com-modelo-proprio": "chave-modelo-proprio",
}

MODELOS_OVERRIDE_TESTE = {
    "loja-com-modelo-proprio": "ollama_chat/qwen2.5:3b-loja-com-modelo-proprio",
}


def _auth(tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {CHAVES_TESTE[tenant_id]}"}


class TenantRepositorioFalso:
    async def autenticar_por_chave(self, *, chave_api: str) -> TenantAutenticado | None:
        for tenant_id, chave_configurada in CHAVES_TESTE.items():
            if chave_configurada == chave_api:
                return TenantAutenticado(
                    tenant_id=tenant_id,
                    modelo_override=MODELOS_OVERRIDE_TESTE.get(tenant_id),
                )
        return None


class MensagemSemFerramenta:
    tool_calls = None
    content = "resposta direta, sem ferramenta"


class GatewayFalso:
    """Nunca pede ferramenta — resultado.resposta_final é reaproveitado, stream_completion não roda."""

    def __init__(self) -> None:
        self.stream_completion_chamado = False
        self.modelo_recebido: str | None = None

    async def complete_with_tools(self, *, mensagens, tools, tenant_id, prompt_id, modelo=None):
        self.modelo_recebido = modelo
        return MensagemSemFerramenta()

    async def stream_completion(
        self, *, mensagens, tenant_id, prompt_id, modelo=None
    ) -> AsyncIterator[str]:
        self.stream_completion_chamado = True
        self.modelo_recebido = modelo
        for pedaco in ["Olá", ", ", "tudo bem?"]:
            yield pedaco


class ChamadaFerramentaFalsa:
    id = "call_1"
    type = "function"
    function = SimpleNamespace(name="consultar_pedido", arguments='{"numero_pedido": "1"}')

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class MensagemComFerramenta:
    content = ""
    tool_calls: ClassVar[list[ChamadaFerramentaFalsa]] = [ChamadaFerramentaFalsa()]


class GatewayFalsoNuncaDecide:
    """Sempre pede ferramenta — força o corte de MAX_ITERACOES, sem resposta_final no estado."""

    def __init__(self) -> None:
        self.mensagens_do_fallback: list[dict] | None = None

    async def complete_with_tools(self, *, mensagens, tools, tenant_id, prompt_id, modelo=None):
        return MensagemComFerramenta()

    async def stream_completion(
        self, *, mensagens, tenant_id, prompt_id, modelo=None
    ) -> AsyncIterator[str]:
        self.mensagens_do_fallback = mensagens
        for pedaco in ["Não", " ", "consegui", " ", "concluir."]:
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
    app.dependency_overrides[get_tenant_repository] = lambda: TenantRepositorioFalso()
    yield
    app.dependency_overrides.clear()


def test_chat_exige_autenticacao() -> None:
    cliente = TestClient(app)

    resposta = cliente.post("/chat", json={"mensagem": "oi"})

    assert resposta.status_code == 401


def test_chat_rejeita_chave_de_api_invalida() -> None:
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers={"Authorization": "Bearer chave-que-nao-existe"},
    )

    assert resposta.status_code == 401


def test_chat_estourar_limite_de_um_tenant_nao_bloqueia_outro_no_mesmo_ip() -> None:
    # Tenants exclusivos deste teste — não compartilham cota com nenhum outro teste do arquivo.
    cliente = TestClient(app)

    for _ in range(20):
        resposta = cliente.post(
            "/chat",
            json={"mensagem": "oi"},
            headers=_auth("loja-teste-rate-limit-a"),
        )
        assert resposta.status_code == 200

    bloqueada = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers=_auth("loja-teste-rate-limit-a"),
    )
    assert bloqueada.status_code == 429

    outra_loja = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers=_auth("loja-teste-rate-limit-b"),
    )
    assert outra_loja.status_code == 200


def _texto_do_stream(corpo: str) -> str:
    """Remonta o texto real a partir das linhas `data: ...` do SSE, ignorando o `[DONE]`."""
    return "".join(
        linha.removeprefix("data: ")
        for linha in corpo.splitlines()
        if linha.startswith("data: ") and linha != "data: [DONE]"
    )


def test_chat_reaproveita_resposta_quando_nao_precisa_de_ferramenta() -> None:
    gateway = GatewayFalso()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers=_auth("loja-azul"),
    )

    assert resposta.status_code == 200
    assert _texto_do_stream(resposta.text) == "resposta direta, sem ferramenta"
    assert "[DONE]" in resposta.text
    assert gateway.stream_completion_chamado is False
    assert gateway.modelo_recebido is None


def test_chat_usa_modelo_override_do_tenant_quando_configurado() -> None:
    gateway = GatewayFalso()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers=_auth("loja-com-modelo-proprio"),
    )

    assert resposta.status_code == 200
    assert gateway.modelo_recebido == MODELOS_OVERRIDE_TESTE["loja-com-modelo-proprio"]


def test_chat_recorre_a_stream_completion_quando_corta_por_max_iteracoes() -> None:
    gateway = GatewayFalsoNuncaDecide()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": "oi"},
        headers=_auth("loja-azul"),
    )

    assert resposta.status_code == 200
    assert _texto_do_stream(resposta.text) == "Não consegui concluir."
    assert "[DONE]" in resposta.text
    # A última tentativa de tool call (nunca executada) não pode sobrar no fim do histórico
    # enviado pro fallback — senão o modelo tenta "completá-la" como texto solto em vez de
    # responder. As tentativas anteriores, já resolvidas com resultado de ferramenta, continuam.
    assert gateway.mensagens_do_fallback is not None
    assert not gateway.mensagens_do_fallback[-2].get("tool_calls")
    assert gateway.mensagens_do_fallback[-1]["role"] == "user"


def test_chat_rejeita_mensagem_vazia() -> None:
    cliente = TestClient(app)

    resposta = cliente.post(
        "/chat",
        json={"mensagem": ""},
        headers=_auth("loja-azul"),
    )

    assert resposta.status_code == 422


def test_chat_nao_loga_pii_crua_do_usuario(caplog: pytest.LogCaptureFixture) -> None:
    cliente = TestClient(app)

    with caplog.at_level("INFO", logger="api.chat"):
        cliente.post(
            "/chat",
            json={"mensagem": "meu e-mail é cliente@exemplo.com, oi"},
            headers=_auth("loja-azul"),
        )

    registros = [r for r in caplog.records if r.name == "api.chat"]
    assert registros
    assert "cliente@exemplo.com" not in registros[0].mensagem_usuario
    assert "[E-MAIL OCULTADO]" in registros[0].mensagem_usuario
