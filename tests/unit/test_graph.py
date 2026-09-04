from types import SimpleNamespace

import pytest

from app.adapters.tools.ferramenta import Ferramenta
from app.orchestration.agent.graph import construir_grafo


class ChamadaFerramentaFalsa:
    def __init__(self, id: str, nome: str, argumentos: str) -> None:
        self.id = id
        self.type = "function"
        self.function = SimpleNamespace(name=nome, arguments=argumentos)

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class MensagemFalsa:
    def __init__(self, content: str = "", tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class GatewayFalso:
    def __init__(self, respostas: list[MensagemFalsa]) -> None:
        self._respostas = iter(respostas)

    async def complete_with_tools(self, *, mensagens, tools, tenant_id, prompt_id):
        return next(self._respostas)


ESTADO_INICIAL = {
    "mensagens": [{"role": "user", "content": "oi"}],
    "tenant_id": "loja-azul",
    "prompt_id": "chat.agente@v1",
    "iteracoes": 0,
    "precisa_ferramenta": False,
}


@pytest.mark.asyncio
async def test_grafo_encerra_sem_chamar_ferramenta_quando_desnecessario() -> None:
    gateway = GatewayFalso([MensagemFalsa(content="oi! tudo bem?")])
    grafo = construir_grafo(gateway, [])

    resultado = await grafo.ainvoke(ESTADO_INICIAL)

    assert resultado["mensagens"] == ESTADO_INICIAL["mensagens"]
    assert resultado["precisa_ferramenta"] is False


@pytest.mark.asyncio
async def test_grafo_executa_ferramenta_e_incorpora_resultado_no_historico() -> None:
    chamada = ChamadaFerramentaFalsa(id="call_1", nome="somar", argumentos='{"a": 2, "b": 3}')
    gateway = GatewayFalso(
        [
            MensagemFalsa(tool_calls=[chamada]),
            MensagemFalsa(content="a soma é 5"),
        ]
    )

    async def executar_soma(argumentos: dict) -> str:
        return f"resultado={argumentos['a'] + argumentos['b']}"

    ferramenta = Ferramenta(
        schema={"type": "function", "function": {"name": "somar", "parameters": {}}},
        executar=executar_soma,
    )
    grafo = construir_grafo(gateway, [ferramenta])

    resultado = await grafo.ainvoke(ESTADO_INICIAL)

    mensagens = resultado["mensagens"]
    assert mensagens[-1] == {"role": "tool", "tool_call_id": "call_1", "content": "resultado=5"}
    assert mensagens[-2]["tool_calls"][0]["function"]["name"] == "somar"


@pytest.mark.asyncio
async def test_grafo_para_apos_numero_maximo_de_iteracoes() -> None:
    chamada = ChamadaFerramentaFalsa(id="call_1", nome="somar", argumentos="{}")
    gateway = GatewayFalso([MensagemFalsa(tool_calls=[chamada]) for _ in range(10)])

    async def executar_sempre_ferramenta(argumentos: dict) -> str:
        return "ok"

    ferramenta = Ferramenta(
        schema={"type": "function", "function": {"name": "somar", "parameters": {}}},
        executar=executar_sempre_ferramenta,
    )
    grafo = construir_grafo(gateway, [ferramenta])

    resultado = await grafo.ainvoke(ESTADO_INICIAL)

    assert resultado["precisa_ferramenta"] is True
    assert resultado["iteracoes"] > 1
