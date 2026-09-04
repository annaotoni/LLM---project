from app.orchestration.prompts.loader import carregar_prompt


def test_carregar_prompt_le_id_versao_e_template() -> None:
    prompt = carregar_prompt("chat_agente_v1.yaml")

    assert prompt.id == "chat.agente"
    assert prompt.version == 1
    assert "Copiloto de Atendimento" in prompt.template
