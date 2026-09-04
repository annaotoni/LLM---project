import asyncpg
from fastapi import Request


async def obter_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool
