import pytest

from app.domain.guardrails.pii import mascarar_pii, mascarar_stream_pii


def test_mascarar_pii_oculta_cpf_email_telefone() -> None:
    texto = "Meu CPF é 123.456.789-00, e-mail teste@exemplo.com, telefone (11) 91234-5678"

    resultado = mascarar_pii(texto)

    assert "123.456.789-00" not in resultado
    assert "teste@exemplo.com" not in resultado
    assert "[CPF OCULTADO]" in resultado
    assert "[E-MAIL OCULTADO]" in resultado


def test_mascarar_pii_preserva_texto_sem_dado_sensivel() -> None:
    texto = "O prazo de entrega é de 5 a 10 dias úteis."

    assert mascarar_pii(texto) == texto


@pytest.mark.asyncio
async def test_mascarar_stream_pii_detecta_email_dividido_entre_pedacos() -> None:
    async def pedacos():
        for parte in ["contato: teste@", "exemplo.com", " obrigado"]:
            yield parte

    saida = "".join([pedaco async for pedaco in mascarar_stream_pii(pedacos())])

    assert "teste@exemplo.com" not in saida
    assert "[E-MAIL OCULTADO]" in saida
    assert saida.endswith("obrigado")


@pytest.mark.asyncio
async def test_mascarar_stream_pii_sem_dado_sensivel_preserva_conteudo() -> None:
    async def pedacos():
        for parte in ["o prazo ", "é de 5 dias"]:
            yield parte

    saida = "".join([pedaco async for pedaco in mascarar_stream_pii(pedacos())])

    assert saida == "o prazo é de 5 dias"
