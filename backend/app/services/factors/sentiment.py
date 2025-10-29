#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪因子计算
"""

from typing import Dict, Any, List, Optional


class SentimentFactor:
    """情绪因子"""

    def __init__(self):
        self.name = "sentiment"
        self.weight = 0.25

    async def calculate(
        self,
        stock_code: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """计算情绪因子评分"""
        try:
            # 新闻情感分析 (40%)
            news_sentiment = self._analyze_news_sentiment(news_data)

            # 资金流向分析 (35%)
            money_flow = self._analyze_money_flow(market_data)

            # 换手率分析 (25%)
            turnover_rate = self._analyze_turnover_rate(market_data)

            # 加权计算总分并归一化到 0-100 区间
            score = (
                news_sentiment * 0.4 +
                money_flow * 0.35 +
                turnover_rate * 0.25
            )
            return min(max(score * 100, 0), 100)
        except Exception as exc:
            print(f"计算情绪因子失败: {exc}")
            return 50.0  # 默认中性评分

    def _analyze_news_sentiment(
        self,
        news_data: Optional[List[Dict[str, Any]]]
    ) -> float:
        """分析新闻情感数据"""
        if not news_data:
            return 0.5

        scores: List[float] = []
        mapping = {"positive": 0.8, "neutral": 0.5, "negative": 0.2}

        for item in news_data:
            if not item:
                continue

            score = item.get("sentiment_score")
            if score is not None:
                try:
                    scores.append(float(score))
                    continue
                except (TypeError, ValueError):
                    pass

            sentiment = item.get("sentiment")
            if sentiment in mapping:
                scores.append(mapping[sentiment])

        if not scores:
            return 0.5

        average = sum(scores) / len(scores)
        return max(0.0, min(1.0, average))

    def _analyze_money_flow(self, market_data: Dict[str, Any]) -> float:
        """分析资金流向"""
        flow = market_data.get("money_flow")
        if flow is None:
            return 0.5

        try:
            # 将资金流向归一化到 0-1，±10亿作为边界
            normalised = max(-1.0, min(1.0, float(flow) / 1_000_000_000))
            return 0.5 + normalised / 2
        except (TypeError, ValueError):
            return 0.5

    def _analyze_turnover_rate(self, market_data: Dict[str, Any]) -> float:
        """分析换手率"""
        rate = market_data.get("turnover_rate")
        if rate is None:
            return 0.5

        try:
            rate = float(rate)
        except (TypeError, ValueError):
            return 0.5

        if 2 <= rate <= 8:
            return 0.8
        if 0.5 <= rate < 2:
            return 0.6
        if 8 < rate <= 15:
            return 0.7
        return 0.4

    def get_factor_info(self) -> Dict[str, Any]:
        """获取情绪因子信息"""
        return {
            "name": self.name,
            "weight": self.weight,
            "description": "情绪因子，包含新闻情感、资金流向、换手率分析",
            "components": [
                {"name": "新闻情感", "weight": 0.4},
                {"name": "资金流向", "weight": 0.35},
                {"name": "换手率", "weight": 0.25}
            ],
            "range": "0-100",
            "higher_better": True
        }
