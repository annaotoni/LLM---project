import asyncpg
from fastapi.testclient import TestClient

from app.api.main import app


def test_health_retorna_ok() -> None:
    cliente = TestClient(app)

    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_ready_retorna_503_quando_banco_indisponivel(monkeypatch) -> None:
    async def conectar_com_falha(*args, **kwargs):
        raise OSError("conexão recusada")

    monkeypatch.setattr(asyncpg, "connect", conectar_com_falha)
    cliente = TestClient(app)

    resposta = cliente.get("/ready")

    assert resposta.status_code == 503


def test_ready_retorna_ok_quando_banco_disponivel(monkeypatch) -> None:
    class ConexaoFalsa:
        async def close(self) -> None:
            return None

    async def conectar_com_sucesso(*args, **kwargs):
        return ConexaoFalsa()

    monkeypatch.setattr(asyncpg, "connect", conectar_com_sucesso)
    cliente = TestClient(app)

    resposta = cliente.get("/ready")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ready"}
