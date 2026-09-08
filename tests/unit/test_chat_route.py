from app.api.routes.chat import _mensagens_para_fallback


def test_mensagens_para_fallback_descarta_tool_call_nunca_executada() -> None:
    mensagens = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "Oi"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_1", "function": {"name": "buscar_documentos"}}],
        },
    ]

    resultado = _mensagens_para_fallback(mensagens)

    assert not any(m.get("tool_calls") for m in resultado)
    assert resultado[-1]["role"] == "user"
    assert "não tente chamar nenhuma função" in resultado[-1]["content"]
    assert resultado[0] == mensagens[0]
    assert resultado[1] == mensagens[1]


def test_mensagens_para_fallback_preserva_historico_quando_ultima_e_resultado_de_ferramenta() -> None:
    mensagens = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "Oi"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "Nenhum documento relevante encontrado."},
    ]

    resultado = _mensagens_para_fallback(mensagens)

    # Já tem resultado da ferramenta — nada pra descartar, só acrescenta a instrução final.
    assert resultado[:-1] == mensagens
    assert resultado[-1]["role"] == "user"
