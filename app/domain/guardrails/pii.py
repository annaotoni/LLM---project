import re
from collections.abc import AsyncIterator

_PADRAO_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Sem \b: um CPF/telefone/cartão colado a uma letra (ex.: "cpf123.456.789-00") não tem fronteira de
# palavra ali (letra e dígito são ambos \w) — \b deixaria esse trecho passar sem mascarar.
_PADRAO_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
_PADRAO_CARTAO = re.compile(r"(?:\d[ -]?){13,19}")
_PADRAO_TELEFONE = re.compile(r"(?:\+55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}")


def mascarar_pii(texto: str) -> str:
    texto = _PADRAO_CPF.sub("[CPF OCULTADO]", texto)
    texto = _PADRAO_EMAIL.sub("[E-MAIL OCULTADO]", texto)
    texto = _PADRAO_CARTAO.sub("[CARTÃO OCULTADO]", texto)
    texto = _PADRAO_TELEFONE.sub("[TELEFONE OCULTADO]", texto)
    return texto


def _fim_do_ultimo_token_completo(texto: str) -> int | None:
    for indice in range(len(texto) - 1, -1, -1):
        if texto[indice].isspace():
            return indice + 1
    return None


async def mascarar_stream_pii(pedacos: AsyncIterator[str]) -> AsyncIterator[str]:
    """Só libera texto até o último espaço — um CPF/e-mail nunca fica cortado entre dois pedaços."""
    buffer = ""
    async for pedaco in pedacos:
        buffer += pedaco
        corte = _fim_do_ultimo_token_completo(buffer)
        if corte is not None:
            yield mascarar_pii(buffer[:corte])
            buffer = buffer[corte:]
    if buffer:
        yield mascarar_pii(buffer)
