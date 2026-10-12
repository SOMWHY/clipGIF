import pytest


@pytest.fixture
def monkeypatch_platform(monkeypatch):
    from app.platforms import registry

    original = list(registry.platform_registry)
    yield monkeypatch
    registry.platform_registry[:] = original
