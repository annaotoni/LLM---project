from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.repositories.postgres.documento_repository import (
    DocumentoRepositoryPostgres,
    _vetor_para_sql,
)
from app.adapters.repositories.postgres.pedido_repository import PedidoRepositoryPostgres
from app.domain.entities.documento import DocumentoRecuperado
from app.domain.entities.pedido import Pedido


# ---------- _vetor_para_sql ----------

def test_vetor_para_sql_formata_corretamente() -> None:
    resultado = _vetor_para_sql([0.1, 0.2, 0.3])
    assert resultado == "[0.1,0.2,0.3]"


def test_vetor_para_sql_lista_vazia() -> None:
    assert _vetor_para_sql([]) == "[]"


def test_vetor_para_sql_valores_negativos_e_zeros() -> None:
    resultado = _vetor_para_sql([-1.0, 0.0, 1.5])
    assert resultado == "[-1.0,0.0,1.5]"


# ---------- DocumentoRepositoryPostgres ----------

def _pool_documento(linhas: list[dict]) -> MagicMock:
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[dict(l) for l in linhas])
    pool.execute = AsyncMock(return_value=None)
    return pool


@pytest.mark.asyncio
async def test_buscar_similares_retorna_documentos_mapeados() -> None:
    pool = _pool_documento([
        {"titulo": "Frete", "conteudo": "Grátis acima de R$150", "distancia": 0.1},
    ])
    repo = DocumentoRepositoryPostgres(pool)

    resultado = await repo.buscar_similares(
        tenant_id="loja-azul", embedding_consulta=[0.1, 0.2], limite=5
    )

    assert len(resultado) == 1
    assert isinstance(resultado[0], DocumentoRecuperado)
    assert resultado[0].titulo == "Frete"
    assert resultado[0].distancia == 0.1


@pytest.mark.asyncio
async def test_buscar_similares_passa_tenant_id_e_vetor_corretos() -> None:
    pool = _pool_documento([])
    repo = DocumentoRepositoryPostgres(pool)
    embedding = [1.0, 2.0, 3.0]

    await repo.buscar_similares(tenant_id="loja-verde", embedding_consulta=embedding, limite=3)

    pool.fetch.assert_called_once()
    args = pool.fetch.call_args.args
    assert args[1] == "loja-verde"
    assert args[2] == "[1.0,2.0,3.0]"
    assert args[3] == 3


@pytest.mark.asyncio
async def test_buscar_similares_lista_vazia_quando_sem_resultados() -> None:
    pool = _pool_documento([])
    repo = DocumentoRepositoryPostgres(pool)

    resultado = await repo.buscar_similares(
        tenant_id="loja-azul", embedding_consulta=[0.1], limite=5
    )

    assert resultado == []


@pytest.mark.asyncio
async def test_inserir_chama_execute_com_parametros_corretos() -> None:
    pool = _pool_documento([])
    repo = DocumentoRepositoryPostgres(pool)
    embedding = [0.5, 0.6]

    await repo.inserir(
        tenant_id="loja-azul", titulo="Política", conteudo="Texto.", embedding=embedding
    )

    pool.execute.assert_called_once()
    args = pool.execute.call_args.args
    assert args[1] == "loja-azul"
    assert args[2] == "Política"
    assert args[3] == "Texto."
    assert args[4] == "[0.5,0.6]"


# ---------- PedidoRepositoryPostgres ----------

def _pool_pedido(linha: dict | None) -> MagicMock:
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=linha)
    return pool


@pytest.mark.asyncio
async def test_buscar_por_numero_retorna_pedido_encontrado() -> None:
    pool = _pool_pedido({
        "numero_pedido": "1001",
        "status": "em transporte",
        "previsao_entrega": date(2026, 9, 10),
        "cliente_nome": "Ana",
    })
    repo = PedidoRepositoryPostgres(pool)

    pedido = await repo.buscar_por_numero(tenant_id="loja-azul", numero_pedido="1001")

    assert isinstance(pedido, Pedido)
    assert pedido.numero_pedido == "1001"
    assert pedido.status == "em transporte"
    assert pedido.previsao_entrega == date(2026, 9, 10)


@pytest.mark.asyncio
async def test_buscar_por_numero_retorna_none_quando_nao_encontrado() -> None:
    pool = _pool_pedido(None)
    repo = PedidoRepositoryPostgres(pool)

    pedido = await repo.buscar_por_numero(tenant_id="loja-azul", numero_pedido="9999")

    assert pedido is None


@pytest.mark.asyncio
async def test_buscar_por_numero_passa_tenant_id_correto() -> None:
    pool = _pool_pedido(None)
    repo = PedidoRepositoryPostgres(pool)

    await repo.buscar_por_numero(tenant_id="loja-verde", numero_pedido="1001")

    pool.fetchrow.assert_called_once()
    args = pool.fetchrow.call_args.args
    assert args[1] == "loja-verde"
    assert args[2] == "1001"


@pytest.mark.asyncio
async def test_buscar_por_numero_sem_previsao_de_entrega() -> None:
    pool = _pool_pedido({
        "numero_pedido": "2002",
        "status": "processando",
        "previsao_entrega": None,
        "cliente_nome": "Bruno",
    })
    repo = PedidoRepositoryPostgres(pool)

    pedido = await repo.buscar_por_numero(tenant_id="loja-azul", numero_pedido="2002")

    assert pedido is not None
    assert pedido.previsao_entrega is None
