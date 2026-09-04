from datetime import date

import pytest

from app.adapters.tools.buscar_documentos import criar_ferramenta_buscar_documentos
from app.adapters.tools.consultar_pedido import criar_ferramenta_consultar_pedido
from app.domain.entities.documento import DocumentoRecuperado
from app.domain.entities.pedido import Pedido


class DocumentoRepositorioFalso:
    def __init__(self, documentos: list[DocumentoRecuperado]) -> None:
        self._documentos = documentos
        self.tenant_id_recebido: str | None = None

    async def buscar_similares(self, *, tenant_id, embedding_consulta, limite):
        self.tenant_id_recebido = tenant_id
        return self._documentos[:limite]

    async def inserir(self, **kwargs) -> None:
        return None


class GatewayFalso:
    async def embed(self, texto: str) -> list[float]:
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_buscar_documentos_isola_por_tenant_e_formata_resultado() -> None:
    repositorio = DocumentoRepositorioFalso(
        [DocumentoRecuperado(titulo="Frete", conteudo="Grátis acima de R$150", distancia=0.1)]
    )
    ferramenta = criar_ferramenta_buscar_documentos(
        tenant_id="loja-azul", repositorio=repositorio, gateway=GatewayFalso(), top_k=4
    )

    resultado = await ferramenta.executar({"consulta": "prazo de frete"})

    assert repositorio.tenant_id_recebido == "loja-azul"
    assert "[Frete]" in resultado
    assert "Grátis acima de R$150" in resultado


@pytest.mark.asyncio
async def test_buscar_documentos_sem_resultado() -> None:
    repositorio = DocumentoRepositorioFalso([])
    ferramenta = criar_ferramenta_buscar_documentos(
        tenant_id="loja-azul", repositorio=repositorio, gateway=GatewayFalso(), top_k=4
    )

    resultado = await ferramenta.executar({"consulta": "garantia"})

    assert resultado == "Nenhum documento relevante encontrado."


class PedidoRepositorioFalso:
    def __init__(self, pedido: Pedido | None) -> None:
        self._pedido = pedido
        self.tenant_id_recebido: str | None = None

    async def buscar_por_numero(self, *, tenant_id, numero_pedido):
        self.tenant_id_recebido = tenant_id
        return self._pedido


@pytest.mark.asyncio
async def test_consultar_pedido_isola_por_tenant() -> None:
    pedido = Pedido(
        numero_pedido="1001",
        status="em transporte",
        previsao_entrega=date(2026, 9, 2),
        cliente_nome="Carla",
    )
    repositorio = PedidoRepositorioFalso(pedido)
    ferramenta = criar_ferramenta_consultar_pedido(tenant_id="loja-azul", repositorio=repositorio)

    resultado = await ferramenta.executar({"numero_pedido": "1001"})

    assert repositorio.tenant_id_recebido == "loja-azul"
    assert "em transporte" in resultado
    assert "2026-09-02" in resultado


@pytest.mark.asyncio
async def test_consultar_pedido_nao_encontrado() -> None:
    repositorio = PedidoRepositorioFalso(None)
    ferramenta = criar_ferramenta_consultar_pedido(tenant_id="loja-azul", repositorio=repositorio)

    resultado = await ferramenta.executar({"numero_pedido": "9999"})

    assert "não encontrado" in resultado


@pytest.mark.asyncio
async def test_consultar_pedido_argumento_ausente_retorna_mensagem_de_erro() -> None:
    repositorio = PedidoRepositorioFalso(None)
    ferramenta = criar_ferramenta_consultar_pedido(tenant_id="loja-azul", repositorio=repositorio)

    resultado = await ferramenta.executar({})

    assert "ausente" in resultado.lower() or "inválido" in resultado.lower()


@pytest.mark.asyncio
async def test_buscar_documentos_argumento_ausente_retorna_mensagem_de_erro() -> None:
    repositorio = DocumentoRepositorioFalso([])
    ferramenta = criar_ferramenta_buscar_documentos(
        tenant_id="loja-azul", repositorio=repositorio, gateway=GatewayFalso(), top_k=4
    )

    resultado = await ferramenta.executar({})

    assert "ausente" in resultado.lower() or "inválido" in resultado.lower()
