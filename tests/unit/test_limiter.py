from starlette.requests import Request

from app.api.limiter import obter_chave_limite


def _request(*, ip: str = "127.0.0.1") -> Request:
    return Request({"type": "http", "headers": [], "client": (ip, 12345)})


def test_obter_chave_limite_combina_ip_e_tenant_ja_resolvido() -> None:
    request = _request()
    request.state.tenant_id = "loja-azul"

    assert obter_chave_limite(request) == "127.0.0.1:loja-azul"


def test_obter_chave_limite_separa_tenants_diferentes_no_mesmo_ip() -> None:
    request_azul = _request()
    request_azul.state.tenant_id = "loja-azul"
    request_verde = _request()
    request_verde.state.tenant_id = "loja-verde"

    assert obter_chave_limite(request_azul) != obter_chave_limite(request_verde)


def test_obter_chave_limite_separa_mesmo_tenant_em_ips_diferentes() -> None:
    request_1 = _request(ip="10.0.0.1")
    request_1.state.tenant_id = "loja-azul"
    request_2 = _request(ip="10.0.0.2")
    request_2.state.tenant_id = "loja-azul"

    assert obter_chave_limite(request_1) != obter_chave_limite(request_2)


def test_obter_chave_limite_sem_tenant_resolvido_usa_valor_padrao() -> None:
    # obter_tenant_id sempre roda antes (dependência) — este caso só cobre o fallback defensivo.
    request = _request()

    assert obter_chave_limite(request) == "127.0.0.1:sem-tenant"
