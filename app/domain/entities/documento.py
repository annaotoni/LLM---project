from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentoRecuperado:
    titulo: str
    conteudo: str
    distancia: float
