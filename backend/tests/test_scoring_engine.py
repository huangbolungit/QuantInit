import pytest

from app.services.scoring.engine import ScoringEngine


@pytest.mark.asyncio
async def test_scoring_engine_basic():
    engine = ScoringEngine()
    market_data = {
        "change_pct": 1.2,
        "turnover_rate": 3.5,
        "money_flow": 1_000_000,
        "current_roe": 12.0,
        "debt_ratio": 35,
        "profit_growth": 0.1,
    }
    res = await engine.calculate_composite_score("000001", market_data)

    assert set(["momentum_score", "sentiment_score", "value_score", "quality_score", "total_score"]).issubset(res.keys())
    assert 0 <= res["total_score"] <= 100

