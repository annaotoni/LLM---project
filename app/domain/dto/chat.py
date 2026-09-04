from pydantic import BaseModel, Field, field_validator


class MensagemChatEntrada(BaseModel):
    mensagem: str = Field(min_length=1, max_length=4000)

    @field_validator("mensagem")
    @classmethod
    def rejeitar_mensagem_em_branco(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("mensagem não pode ser vazia")
        return texto
