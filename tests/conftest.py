import pytest

from app.config.settings import get_settings


@pytest.fixture(autouse=True)
def variaveis_de_ambiente_de_teste(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Unitário/feature usam DB fake; eval precisa do .env real (Postgres/Ollama de verdade)."""
    if request.node.get_closest_marker("eval") is None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://teste:teste@localhost:5432/teste")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
