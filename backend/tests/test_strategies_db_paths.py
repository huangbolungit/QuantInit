import pytest
from httpx import AsyncClient
from datetime import datetime

from main import app
from app.services.strategy_engine import get_strategy_engine, TradingSignal, SignalType


@pytest.mark.asyncio
async def test_get_strategy_detail_db_first():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create strategy (persists)
        payload = {
            "name": "detail-db-first",
            "strategy_type": "mean_reversion",
            "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
            "stock_pool": ["000001"],
            "rebalance_frequency": 10,
        }
        r = await ac.post("/api/strategies", json=payload)
        assert r.status_code == 200
        sid = r.json()["id"]

        # query detail (DB preferred)
        r2 = await ac.get(f"/api/strategies/{sid}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["id"] == sid
        assert data["parameters"]["lookback_period"] == 10


@pytest.mark.asyncio
async def test_latest_signals_db_first(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create strategy
        payload = {
            "name": "signals-db-first",
            "strategy_type": "mean_reversion",
            "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
            "stock_pool": ["000001"],
            "rebalance_frequency": 10,
        }
        r = await ac.post("/api/strategies", json=payload)
        assert r.status_code == 200
        sid = r.json()["id"]

        # mock engine.generate_signals to return one signal
        engine = get_strategy_engine()

        async def fake_generate_all():
            now = datetime.now()
            return [
                TradingSignal(
                    id="sig-1",
                    strategy_id=sid,
                    stock_code="000001",
                    signal_type=SignalType.BUY,
                    confidence=0.8,
                    price=10.0,
                    timestamp=now,
                    reason="test",
                )
            ]

        monkeypatch.setattr(engine, "generate_signals", fake_generate_all)

        # call batch generate -> persists
        r2 = await ac.post("/api/signals/generate")
        assert r2.status_code == 200

        # latest signals should read from DB first
        r3 = await ac.get("/api/signals/latest", params={"limit": 10})
        assert r3.status_code == 200
        items = r3.json()
        assert any(s["id"] == "sig-1" for s in items)


@pytest.mark.asyncio
async def test_update_and_delete_strategy_persisted():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create
        payload = {
            "name": "update-delete",
            "strategy_type": "mean_reversion",
            "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
            "stock_pool": ["000001", "000002"],
            "rebalance_frequency": 10,
        }
        r = await ac.post("/api/strategies", json=payload)
        assert r.status_code == 200
        sid = r.json()["id"]

        # update
        upd = {
            "parameters": {"lookback_period": 15},
            "stock_pool": ["000003"],
        }
        r2 = await ac.put(f"/api/strategies/{sid}", json=upd)
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["parameters"]["lookback_period"] == 15
        assert data2["stock_pool"] == ["000003"]

        # delete
        r3 = await ac.delete(f"/api/strategies/{sid}")
        assert r3.status_code == 200

        # list should not include the strategy (DB preferred)
        r4 = await ac.get("/api/strategies")
        assert r4.status_code == 200
        items = r4.json()
        assert not any(it["id"] == sid for it in items)

