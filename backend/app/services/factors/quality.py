#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
质量因子计算
"""

from typing import Dict, Any, List
import numpy as np
from datetime import datetime


class QualityFactor:
    """质量因子"""

    def __init__(self):
        self.name = "quality"
        self.weight = 0.20

    async def calculate(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """计算质量因子评分"""
        try:
            # TODO: 实现真实的质量分析
            # 这里使用模拟数据

            # ROE稳定性 (35%)
            roe_stability = self._analyze_roe_stability(stock_code, market_data)

            # 负债率 (30%)
            debt_ratio = self._analyze_debt_ratio(stock_code, market_data)

            # 盈利一致性 (35%)
            profit_consistency = self._analyze_profit_consistency(stock_code, market_data)

            # 加权计算总分
            score = (
                roe_stability * 0.35 +
                debt_ratio * 0.30 +
                profit_consistency * 0.35
            )

            # 归一化到0-100
            return min(max(score * 100, 0), 100)

        except Exception as e:
            print(f"计算质量因子失败: {e}")
            return 50.0  # 默认中性评分

    def _analyze_roe_stability(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """分析ROE稳定性"""
        try:
            if "roe_data" in market_data:
                roe_history = market_data["roe_data"]
                if len(roe_history) >= 3:
                    # 计算ROE的标准差，标准差越小越稳定
                    roe_std = np.std(roe_history)
                    roe_avg = np.mean(roe_history)

                    # 稳定性评分：标准差越小越好，平均值越高越好
                    stability_score = max(0, 1 - roe_std / 10)  # 标准差>10给予0分
                    level_score = min(roe_avg / 15, 1.0)  # ROE平均>15%给予满分

                    return (stability_score * 0.6 + level_score * 0.4)

            # 使用当前ROE作为参考
            if "current_roe" in market_data:
                roe = market_data["current_roe"]
                if roe > 15:
                    return 0.8
                elif roe > 10:
                    return 0.6
                elif roe > 5:
                    return 0.4
                elif roe > 0:
                    return 0.2
                else:
                    return 0.1

            return 0.5
        except:
            return 0.5

    def _analyze_debt_ratio(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """分析负债率"""
        try:
            if "debt_ratio" in market_data:
                debt = market_data["debt_ratio"]

                # 负债率适中最好，过高或过低都减分
                if 20 <= debt <= 40:
                    return 1.0
                elif 10 <= debt < 20:
                    return 0.9
                elif 40 < debt <= 60:
                    return 0.8
                elif 5 <= debt < 10:
                    return 0.7
                elif 60 < debt <= 80:
                    return 0.5
                elif debt > 80:
                    return 0.2
                else:
                    return 0.5

            return 0.7  # 默认给予中性偏好的评分
        except:
            return 0.7

    def _analyze_profit_consistency(self, stock_code: str, market_data: Dict[str, Any]) -> float:
        """分析盈利一致性"""
        try:
            if "profit_history" in market_data:
                profit_history = market_data["profit_history"]
                if len(profit_history) >= 3:
                    # 计算盈利增长的年份占比
                    growth_years = 0
                    for i in range(1, len(profit_history)):
                        if profit_history[i] > profit_history[i-1]:
                            growth_years += 1

                    consistency_score = growth_years / (len(profit_history) - 1)
                    return consistency_score

            # 使用当前盈利增长情况
            if "profit_growth" in market_data:
                growth = market_data["profit_growth"]
                if growth > 0.2:  # >20%
                    return 0.9
                elif growth > 0.1:  # >10%
                    return 0.8
                elif growth > 0:  # >0%
                    return 0.6
                elif growth > -0.1:  # >-10%
                    return 0.4
                else:
                    return 0.2

            return 0.5
        except:
            return 0.5

    def get_factor_info(self) -> Dict[str, Any]:
        """获取因子信息"""
        return {
            "name": self.name,
            "weight": self.weight,
            "description": "质量因子，包含ROE稳定性、负债率、盈利一致性分析",
            "components": [
                {"name": "ROE稳定性", "weight": 0.35},
                {"name": "负债率", "weight": 0.30},
                {"name": "盈利一致性", "weight": 0.35}
            ],
            "range": "0-100",
            "higher_better": True
        }