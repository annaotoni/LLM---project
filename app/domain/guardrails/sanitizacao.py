_MARCADORES_SUSPEITOS = ("system:", "assistant:", "###", "ignore as instruções anteriores")
LIMITE_CARACTERES = 2000


def sanitizar_conteudo_externo(texto: str) -> str:
    """Neutraliza tentativas de injeção em conteúdo que não veio do usuário direto (RAG, ferramentas)."""
    texto_sanitizado = texto[:LIMITE_CARACTERES]
    minusculo = texto_sanitizado.lower()
    for marcador in _MARCADORES_SUSPEITOS:
        if marcador in minusculo:
            indice = minusculo.index(marcador)
            texto_sanitizado = (
                texto_sanitizado[:indice]
                + "[trecho removido]"
                + texto_sanitizado[indice + len(marcador) :]
            )
            minusculo = texto_sanitizado.lower()
    return texto_sanitizado
