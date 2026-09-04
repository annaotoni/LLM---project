import pytest
from pydantic import ValidationError

from app.domain.dto.chat import MensagemChatEntrada


def test_rejeita_mensagem_só_com_espacos() -> None:
    with pytest.raises(ValidationError):
        MensagemChatEntrada(mensagem="    ")


def test_remove_espacos_nas_bordas() -> None:
    entrada = MensagemChatEntrada(mensagem="  qual o prazo de entrega?  ")

    assert entrada.mensagem == "qual o prazo de entrega?"
