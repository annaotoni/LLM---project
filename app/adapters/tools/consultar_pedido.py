from typing import Any

from app.adapters.repositories.contracts.pedido_repository_interface import (
    PedidoRepositoryInterface,
)
from app.adapters.tools.ferramenta import Ferramenta

SCHEMA = {
    "type": "function",
    "function": {
        "name": "consultar_pedido",
        "description": "Consulta o status e a previsao de entrega de um pedido pelo numero.",
        "parameters": {
            "type": "object",
            "properties": {
                "numero_pedido": {
                    "type": "string",
                    "description": "Numero do pedido informado pelo cliente.",
                },
            },
            "required": ["numero_pedido"],
        },
    },
}


def criar_ferramenta_consultar_pedido(
    *,
    tenant_id: str,
    repositorio: PedidoRepositoryInterface,
) -> Ferramenta:
    """Isola a consulta por tenant na origem — um pedido de outra loja nunca é alcançável."""

    async def executar(argumentos: dict[str, Any]) -> str:
        numero_pedido = argumentos.get("numero_pedido")
        if not numero_pedido:
            return "Parâmetro numero_pedido ausente ou inválido."
        pedido = await repositorio.buscar_por_numero(
            tenant_id=tenant_id, numero_pedido=numero_pedido
        )
        if pedido is None:
            return f"Pedido {numero_pedido} não encontrado."
        previsao = (
            pedido.previsao_entrega.isoformat() if pedido.previsao_entrega else "não informada"
        )
        return (
            f"Pedido {pedido.numero_pedido}: status = {pedido.status}, "
            f"previsão de entrega = {previsao}."
        )

    return Ferramenta(schema=SCHEMA, executar=executar)
