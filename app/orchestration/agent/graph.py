import json
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, StateGraph

from app.adapters.tools.ferramenta import Ferramenta
from app.orchestration.gateway.model_gateway import ModelGateway

MAX_ITERACOES = 4


class EstadoAgente(TypedDict):
    mensagens: list[dict[str, Any]]
    tenant_id: str
    prompt_id: str
    iteracoes: int
    precisa_ferramenta: bool
    gateway: NotRequired[Any]
    ferramentas: NotRequired[list[Any]]
    resposta_final: NotRequired[str]
    modelo: NotRequired[str | None]


def _tool_call_para_dict(tool_call: Any) -> dict[str, Any]:
    if hasattr(tool_call, "model_dump"):
        return tool_call.model_dump()
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {
            "name": tool_call.function.name,
            "arguments": tool_call.function.arguments,
        },
    }


async def _chamar_modelo(estado: EstadoAgente) -> dict[str, Any]:
    gateway: ModelGateway = estado["gateway"]
    ferramentas: list[Ferramenta] = estado.get("ferramentas", [])
    schemas = [f.schema for f in ferramentas]
    mensagem = await gateway.complete_with_tools(
        mensagens=estado["mensagens"],
        tools=schemas,
        tenant_id=estado["tenant_id"],
        prompt_id=estado["prompt_id"],
        modelo=estado.get("modelo"),
    )
    if not mensagem.tool_calls:
        # O modelo já gerou a resposta final aqui — reaproveitada em vez de pedir de novo em
        # stream_completion, que dobraria o tempo de resposta sem mudar o conteúdo.
        return {
            "iteracoes": estado["iteracoes"] + 1,
            "precisa_ferramenta": False,
            "resposta_final": mensagem.content or "",
        }

    mensagem_assistente = {
        "role": "assistant",
        "content": mensagem.content or "",
        "tool_calls": [_tool_call_para_dict(tc) for tc in mensagem.tool_calls],
    }
    return {
        "mensagens": [*estado["mensagens"], mensagem_assistente],
        "iteracoes": estado["iteracoes"] + 1,
        "precisa_ferramenta": True,
    }


async def _executar_ferramentas(estado: EstadoAgente) -> dict[str, Any]:
    ferramentas: list[Ferramenta] = estado.get("ferramentas", [])
    mapa_ferramentas = {f.nome: f for f in ferramentas}
    ultima_mensagem = estado["mensagens"][-1]
    resultados = []
    for chamada in ultima_mensagem["tool_calls"]:
        ferramenta = mapa_ferramentas.get(chamada["function"]["name"])
        argumentos = json.loads(chamada["function"]["arguments"])
        conteudo = (
            await ferramenta.executar(argumentos) if ferramenta else "Ferramenta desconhecida."
        )
        resultados.append(
            {"role": "tool", "tool_call_id": chamada["id"], "content": conteudo}
        )
    return {"mensagens": [*estado["mensagens"], *resultados]}


def _decidir_proximo_passo(estado: EstadoAgente) -> str:
    if estado["precisa_ferramenta"] and estado["iteracoes"] <= MAX_ITERACOES:
        return "ferramentas"
    return END


def _compilar() -> Any:
    grafo = StateGraph(EstadoAgente)
    grafo.add_node("modelo", _chamar_modelo)
    grafo.add_node("ferramentas", _executar_ferramentas)
    grafo.set_entry_point("modelo")
    grafo.add_conditional_edges(
        "modelo", _decidir_proximo_passo, {"ferramentas": "ferramentas", END: END}
    )
    grafo.add_edge("ferramentas", "modelo")
    return grafo.compile()


# Compilado na importação do módulo — uma vez por processo.
GRAFO = _compilar()


def construir_grafo(gateway: ModelGateway, ferramentas: list[Ferramenta]) -> Any:
    """Gateway e ferramentas são passados via estado em ainvoke; wrapper mantido para compatibilidade com testes."""
    return GRAFO
