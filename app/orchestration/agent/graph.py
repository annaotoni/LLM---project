import json
from typing import Any, TypedDict

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


def construir_grafo(gateway: ModelGateway, ferramentas: list[Ferramenta]):
    mapa_ferramentas = {ferramenta.nome: ferramenta for ferramenta in ferramentas}
    schemas = [ferramenta.schema for ferramenta in ferramentas]

    async def chamar_modelo(estado: EstadoAgente) -> dict[str, Any]:
        mensagem = await gateway.complete_with_tools(
            mensagens=estado["mensagens"],
            tools=schemas,
            tenant_id=estado["tenant_id"],
            prompt_id=estado["prompt_id"],
        )
        if not mensagem.tool_calls:
            return {"iteracoes": estado["iteracoes"] + 1, "precisa_ferramenta": False}

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

    async def executar_ferramentas(estado: EstadoAgente) -> dict[str, Any]:
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

    def decidir_proximo_passo(estado: EstadoAgente) -> str:
        if estado["precisa_ferramenta"] and estado["iteracoes"] <= MAX_ITERACOES:
            return "ferramentas"
        return END

    grafo = StateGraph(EstadoAgente)
    grafo.add_node("modelo", chamar_modelo)
    grafo.add_node("ferramentas", executar_ferramentas)
    grafo.set_entry_point("modelo")
    grafo.add_conditional_edges(
        "modelo", decidir_proximo_passo, {"ferramentas": "ferramentas", END: END}
    )
    grafo.add_edge("ferramentas", "modelo")

    return grafo.compile()
