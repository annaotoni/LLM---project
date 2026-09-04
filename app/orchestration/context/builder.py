from dataclasses import dataclass

from app.orchestration.prompts.loader import carregar_prompt


@dataclass(frozen=True)
class ContextoConversa:
    mensagens: list[dict[str, str]]
    prompt_id: str


def construir_contexto(mensagem_usuario: str) -> ContextoConversa:
    """Recria o contexto do zero a cada chamada — o modelo não tem memória própria."""
    prompt_sistema = carregar_prompt("chat_agente_v1.yaml")
    mensagens = [
        {"role": "system", "content": prompt_sistema.template},
        {"role": "user", "content": mensagem_usuario},
    ]
    return ContextoConversa(
        mensagens=mensagens,
        prompt_id=f"{prompt_sistema.id}@v{prompt_sistema.version}",
    )
