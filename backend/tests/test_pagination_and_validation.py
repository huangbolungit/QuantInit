import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from main import app
from app.services.strategy_engine import get_strategy_engine, TradingSignal, SignalType


@pytest.mark.asyncio
async def test_strategies_pagination_and_validation():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create two strategies
        for name in ["s-pg-1", "s-pg-2"]:
            payload = {
                "name": name,
                "strategy_type": "mean_reversion",
                "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
                "stock_pool": ["000001"],
                "rebalance_frequency": 10,
            }
            r = await ac.post("/api/strategies", json=payload)
            assert r.status_code == 200

        # invalid limit
        r1 = await ac.get("/api/strategies", params={"limit": -1})
        assert r1.status_code == 400
        # invalid offset
        r2 = await ac.get("/api/strategies", params={"offset": -2})
        assert r2.status_code == 400

        # pagination: limit=1 offset=0 vs offset=1 -> different ids
        a = await ac.get("/api/strategies", params={"limit": 1, "offset": 0})
        b = await ac.get("/api/strategies", params={"limit": 1, "offset": 1})
        assert a.status_code == 200 and b.status_code == 200
        assert a.json()[0]["id"] != b.json()[0]["id"]


@pytest.mark.asyncio
async def test_signals_pagination_and_validation(monkeypatch):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create strategy
        payload = {
            "name": "sig-pg",
            "strategy_type": "mean_reversion",
            "parameters": {"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
            "stock_pool": ["000001"],
            "rebalance_frequency": 10,
        }
        r = await ac.post("/api/strategies", json=payload)
        assert r.status_code == 200
        sid = r.json()["id"]

        # patch engine to generate 3 signals with distinct timestamps
        engine = get_strategy_engine()
        now = datetime.now()

        async def fake_generate_all():
            return [
                TradingSignal(
                    id="sig-a",
                    strategy_id=sid,
                    stock_code="000001",
                    signal_type=SignalType.BUY,
                    confidence=0.9,
                    price=10.0,
                    timestamp=now + timedelta(seconds=2),
                    reason="A",
                ),
                TradingSignal(
                    id="sig-b",
                    strategy_id=sid,
                    stock_code="000001",
                    signal_type=SignalType.SELL,
                    confidence=0.8,
                    price=10.5,
                    timestamp=now + timedelta(seconds=1),
                    reason="B",
                ),
                TradingSignal(
                    id="sig-c",
                    strategy_id=sid,
                    stock_code="000001",
                    signal_type=SignalType.HOLD,
                    confidence=0.7,
                    price=9.8,
                    timestamp=now,
                    reason="C",
                ),
            ]

        monkeypatch.setattr(engine, "generate_signals", fake_generate_all)

        # persist 3 signals
        r2 = await ac.post("/api/signals/generate")
        assert r2.status_code == 200

        # invalid limit/offset
        bad1 = await ac.get("/api/signals/latest", params={"limit": 0})
        assert bad1.status_code == 400
        bad2 = await ac.get("/api/signals/latest", params={"offset": -1})
        assert bad2.status_code == 400

        # pagination check: order desc by timestamp
        first = await ac.get("/api/signals/latest", params={"limit": 1, "offset": 0})
        second = await ac.get("/api/signals/latest", params={"limit": 1, "offset": 1})
        third = await ac.get("/api/signals/latest", params={"limit": 1, "offset": 2})
        ids = [r.json()[0]["id"] for r in (first, second, third)]
        assert ids == ["sig-a", "sig-b", "sig-c"]


@pytest.mark.asyncio
async def test_db_error_fallback_to_memory(monkeypatch):
    """当DB读取抛异常时，接口应回退到内存数据，不影响可用性。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # prepare engine memory signals
        engine = get_strategy_engine()
        from datetime import datetime
        engine.signal_history.clear()
        engine.signal_history.extend(
            [
                TradingSignal(
                    id="mem-1",
                    strategy_id="mem-strat",
                    stock_code="000001",
                    signal_type=SignalType.BUY,
                    confidence=0.5,
                    price=1.0,
                    timestamp=datetime.now(),
                    reason="mem",
                )
            ]
        )

        # monkeypatch list_latest_signals to raise
        import app.services.strategies.persistence as persistence

        async def boom(*args, **kwargs):  # pragma: no cover
            raise RuntimeError("db down")

        monkeypatch.setattr(persistence, "list_latest_signals", boom)

        r = await ac.get("/api/signals/latest", params={"limit": 1})
        assert r.status_code == 200
        assert r.json()[0]["id"] == "mem-1"

