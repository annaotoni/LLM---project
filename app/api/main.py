from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.limiter import limiter
from app.api.routes import chat, health
from app.config.logging import configurar_logging
from app.config.settings import get_settings

configurar_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # min_size=0: conecta sob demanda, então a API sobe mesmo com o banco temporariamente fora.
    app.state.pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=0)
    yield
    await app.state.pool.close()


app = FastAPI(title="Copiloto de Atendimento", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health.router)
app.include_router(chat.router)
