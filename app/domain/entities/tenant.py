from dataclasses import dataclass


@dataclass(frozen=True)
class TenantAutenticado:
    tenant_id: str
    modelo_override: str | None
