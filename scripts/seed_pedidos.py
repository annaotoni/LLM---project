import asyncio
from datetime import date

import asyncpg

from app.config.settings import get_settings

PEDIDOS = [
    ("loja-azul", "1001", "em transporte", date(2026, 9, 2), "Carla Mendes"),
    ("loja-azul", "1002", "entregue", date(2026, 8, 20), "Bruno Alves"),
    ("loja-azul", "1003", "processando", date(2026, 9, 10), "Fernanda Lima"),
    ("loja-verde", "2001", "em transporte", date(2026, 9, 5), "Diego Souza"),
    ("loja-verde", "2002", "entregue", date(2026, 8, 15), "Patrícia Rocha"),
]


async def semear() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    try:
        for tenant_id, numero_pedido, status, previsao_entrega, cliente_nome in PEDIDOS:
            await pool.execute(
                """
                INSERT INTO pedidos (tenant_id, numero_pedido, status, previsao_entrega, cliente_nome)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, numero_pedido) DO UPDATE
                SET status = EXCLUDED.status,
                    previsao_entrega = EXCLUDED.previsao_entrega,
                    cliente_nome = EXCLUDED.cliente_nome
                """,
                tenant_id,
                numero_pedido,
                status,
                previsao_entrega,
                cliente_nome,
            )
            print(f"[{tenant_id}] pedido {numero_pedido} — semeado")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(semear())
