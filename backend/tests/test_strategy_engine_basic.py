import pytest

from app.services.strategy_engine import get_strategy_engine


@pytest.mark.asyncio
async def test_create_strategy_mean_reversion():
    engine = get_strategy_engine()
    strat_id = await engine.create_strategy(
        name="test-mr",
        strategy_type="mean_reversion",
        parameters={"lookback_period": 10, "buy_threshold": -0.05, "sell_threshold": 0.03},
        stock_pool=["000001", "000002"],
        rebalance_frequency=10,
    )

    assert strat_id in engine.active_strategies
    cfg = engine.active_strategies[strat_id]
    assert cfg.strategy_type == "mean_reversion"
    assert cfg.parameters["lookback_period"] == 10

