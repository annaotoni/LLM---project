from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    template: str


@lru_cache
def carregar_prompt(nome_arquivo: str) -> Prompt:
    caminho = PROMPTS_DIR / nome_arquivo
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return Prompt(id=dados["id"], version=dados["version"], template=dados["template"])
