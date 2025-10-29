import pytest
from httpx import AsyncClient

from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in {"healthy", "ok", "running"}
    assert "version" in data


@pytest.mark.asyncio
async def test_market_overview_with_mock(monkeypatch):
    class FakeManager:
        async def get_market_overview(self):
            return {"indices": [{"code": "000001", "name": "上证指数", "change_pct": 0.12}]}

    # Patch the DataSourceManager used inside the endpoint module
    import app.api.endpoints.market as market_module

    monkeypatch.setattr(market_module, "DataSourceManager", lambda: FakeManager())

    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/market/overview")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
    assert isinstance(payload.get("data"), dict)
