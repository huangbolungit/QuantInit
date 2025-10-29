import pytest

from app.services.factors.sentiment import SentimentFactor


@pytest.mark.asyncio
async def test_sentiment_factor_deterministic():
    factor = SentimentFactor()
    market_data = {
        "money_flow": 500_000_000,
        "turnover_rate": 4.5
    }
    news_data = [
        {"sentiment": "positive"},
        {"sentiment_score": 0.4}
    ]

    score_first = await factor.calculate("000001", market_data, news_data)
    score_second = await factor.calculate("000001", market_data, news_data)

    assert score_first == pytest.approx(score_second)
    assert 0 <= score_first <= 100
