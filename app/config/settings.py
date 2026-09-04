from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, carregadas do ambiente (.env)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str

    llm_provider: str = "ollama"
    llm_model: str = "ollama_chat/qwen2.5:3b"
    llm_embedding_model: str = "ollama/all-minilm"
    ollama_base_url: str = "http://ollama:11434"
    rag_top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
