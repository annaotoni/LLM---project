from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def obter_chave_limite(request: Request) -> str:
    """Cota por (IP, tenant) — um tenant abusando não consome a cota dos outros atrás do mesmo IP.

    O tenant já foi autenticado contra o banco em `obter_tenant_id` (única consulta — este
    key_func só lê o resultado em `request.state`, não repete a busca).
    """
    tenant_id = getattr(request.state, "tenant_id", "sem-tenant")
    return f"{get_remote_address(request)}:{tenant_id}"


limiter = Limiter(key_func=obter_chave_limite)
