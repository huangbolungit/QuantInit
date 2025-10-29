import pytest
from httpx import AsyncClient

from main import app


@pytest.mark.asyncio
async def test_create_and_list_strategy_persisted():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create
        payload = {
            "name": "pytest-mr",
            "strategy_type": "mean_reversion",
            "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
            "stock_pool": ["000001", "000002"],
            "rebalance_frequency": 10,
        }
        resp = await ac.post("/api/strategies", json=payload)
        assert resp.status_code == 200
        created = resp.json()
        assert created["id"]

        # list
        resp2 = await ac.get("/api/strategies")
        assert resp2.status_code == 200
        items = resp2.json()
        assert any(it["id"] == created["id"] for it in items)

