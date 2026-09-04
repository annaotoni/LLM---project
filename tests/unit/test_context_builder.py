from app.orchestration.context.builder import construir_contexto


def test_construir_contexto_inclui_prompt_sistema_e_mensagem_usuario() -> None:
    contexto = construir_contexto("Qual o prazo de entrega?")

    assert contexto.mensagens[0]["role"] == "system"
    assert contexto.mensagens[1] == {"role": "user", "content": "Qual o prazo de entrega?"}
    assert contexto.prompt_id == "chat.agente@v1"
