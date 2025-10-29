#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动量因子计算器
"""

from typing import Dict, Any, List, Optional
import asyncio
import math
from datetime import datetime, timedelta


class MomentumFactor:
    """动量因子计算器"""

    def __init__(self):
        self.short_period = 5   # 短期均线周期
        self.medium_period = 20  # 中期均线周期
        self.long_period = 60    # 长期均线周期
        self.rsi_period = 14     # RSI周期

    async def calculate(
        self,
        stock_code: str,
        market_data: Dict[str, Any],
        kline_data: Optional[List[Dict]] = None
    ) -> float:
        """
        计算动量因子得分 (0-100分)

        动量因子包括：
        1. 均线排列得分
        2. RSI相对强弱指标
        3. 价格动量
        4. 成交量动量
        """

        try:
            # 如果没有K线数据，使用基础市场数据计算简化版本
            if not kline_data:
                return self._calculate_simple_momentum(market_data)

            # 1. 均线排列得分 (权重: 30%)
            ma_score = self._calculate_ma_score(kline_data)

            # 2. RSI得分 (权重: 25%)
            rsi_score = self._calculate_rsi_score(kline_data)

            # 3. 价格动量得分 (权重: 25%)
            price_momentum_score = self._calculate_price_momentum(kline_data)

            # 4. 成交量动量得分 (权重: 20%)
            volume_momentum_score = self._calculate_volume_momentum(kline_data)

            # 综合得分
            total_score = (
                ma_score * 0.30 +
                rsi_score * 0.25 +
                price_momentum_score * 0.25 +
                volume_momentum_score * 0.20
            )

            return round(total_score, 2)

        except Exception as e:
            print(f"计算股票 {stock_code} 动量因子失败: {e}")
            return 50.0

    def _calculate_simple_momentum(self, market_data: Dict[str, Any]) -> float:
        """基于基础市场数据计算简化动量得分"""
        change_pct = market_data.get('change_pct', 0)
        turnover_rate = market_data.get('turnover_rate', 0)

        # 基于涨跌幅的得分
        if change_pct > 5:
            price_score = 90
        elif change_pct > 2:
            price_score = 75
        elif change_pct > 0:
            price_score = 60
        elif change_pct > -2:
            price_score = 45
        elif change_pct > -5:
            price_score = 30
        else:
            price_score = 15

        # 基于换手率的得分 (适度活跃为好)
        if 1 <= turnover_rate <= 5:
            volume_score = 80
        elif 0.5 <= turnover_rate < 1 or 5 < turnover_rate <= 10:
            volume_score = 65
        elif turnover_rate < 0.5 or turnover_rate > 10:
            volume_score = 40
        else:
            volume_score = 50

        return (price_score * 0.7 + volume_score * 0.3)

    def _calculate_ma_score(self, kline_data: List[Dict]) -> float:
        """计算均线排列得分"""
        if len(kline_data) < self.long_period:
            return 50.0

        # 获取最近的价格数据
        recent_prices = [item['close'] for item in kline_data[-self.long_period:]]

        # 计算均线
        short_ma = sum(recent_prices[-self.short_period:]) / self.short_period
        medium_ma = sum(recent_prices[-self.medium_period:]) / self.medium_period
        long_ma = sum(recent_prices) / self.long_period
        current_price = recent_prices[-1]

        # 均线排列评分
        # 理想状态：短期 > 中期 > 长期，且价格在短期均线上方
        if (current_price > short_ma > medium_ma > long_ma):
            # 计算均线发散程度
            short_long_ratio = short_ma / long_ma
            if short_long_ratio > 1.05:
                return 95.0  # 强势多头排列
            else:
                return 85.0  # 多头排列
        elif (current_price > short_ma > medium_ma):
            return 70.0  # 部分多头排列
        elif current_price > medium_ma:
            return 55.0  # 价格在中期均线上方
        elif current_price > long_ma:
            return 45.0  # 价格在长期均线上方
        else:
            # 均线向下排列
            if short_ma < medium_ma < long_ma:
                return 20.0  # 空头排列
            else:
                return 35.0  # 部分空头排列

    def _calculate_rsi_score(self, kline_data: List[Dict]) -> float:
        """计算RSI得分"""
        if len(kline_data) < self.rsi_period + 1:
            return 50.0

        # 计算RSI
        closes = [item['close'] for item in kline_data]
        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        # 计算平均收益和损失
        recent_gains = gains[-self.rsi_period:]
        recent_losses = losses[-self.rsi_period:]

        avg_gain = sum(recent_gains) / self.rsi_period if recent_gains else 0
        avg_loss = sum(recent_losses) / self.rsi_period if recent_losses else 0

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # RSI评分
        if 30 <= rsi <= 70:
            # RSI在正常范围内，越接近50越好
            score = 100 - abs(rsi - 50) * 2
        elif rsi < 30:
            # 超卖区域
            score = 60 + (30 - rsi)
        else:
            # 超买区域
            score = 60 - (rsi - 70)

        return round(score, 2)

    def _calculate_price_momentum(self, kline_data: List[Dict]) -> float:
        """计算价格动量得分"""
        if len(kline_data) < 20:
            return 50.0

        # 取不同周期的收益率
        current_price = kline_data[-1]['close']

        # 5日收益率
        price_5d_ago = kline_data[-6]['close'] if len(kline_data) >= 6 else kline_data[0]['close']
        return_5d = (current_price - price_5d_ago) / price_5d_ago * 100

        # 10日收益率
        price_10d_ago = kline_data[-11]['close'] if len(kline_data) >= 11 else kline_data[0]['close']
        return_10d = (current_price - price_10d_ago) / price_10d_ago * 100

        # 20日收益率
        price_20d_ago = kline_data[-21]['close'] if len(kline_data) >= 21 else kline_data[0]['close']
        return_20d = (current_price - price_20d_ago) / price_20d_ago * 100

        # 综合评分
        score_5d = min(100, max(0, 50 + return_5d * 10))  # 5日权重最高
        score_10d = min(100, max(0, 50 + return_10d * 8))
        score_20d = min(100, max(0, 50 + return_20d * 5))

        total_score = score_5d * 0.5 + score_10d * 0.3 + score_20d * 0.2

        return round(total_score, 2)

    def _calculate_volume_momentum(self, kline_data: List[Dict]) -> float:
        """计算成交量动量得分"""
        if len(kline_data) < 10:
            return 50.0

        # 计算成交量均线
        recent_volumes = [item['volume'] for item in kline_data[-10:]]
        current_volume = recent_volumes[-1]
        avg_volume = sum(recent_volumes[:-1]) / (len(recent_volumes) - 1)

        # 计算成交量比率
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # 计算成交额动量
        recent_turnovers = [item['turnover'] for item in kline_data[-10:]]
        current_turnover = recent_turnovers[-1]
        avg_turnover = sum(recent_turnovers[:-1]) / (len(recent_turnovers) - 1)

        turnover_ratio = current_turnover / avg_turnover if avg_turnover > 0 else 1

        # 综合评分
        if 0.8 <= volume_ratio <= 3.0:  # 成交量适度放大
            volume_score = 80
        elif 0.5 <= volume_ratio < 0.8 or 3.0 < volume_ratio <= 5.0:
            volume_score = 65
        elif volume_ratio < 0.5 or volume_ratio > 5.0:
            volume_score = 40
        else:
            volume_score = 50

        if 0.8 <= turnover_ratio <= 3.0:  # 成交额适度放大
            turnover_score = 80
        elif 0.5 <= turnover_ratio < 0.8 or 3.0 < turnover_ratio <= 5.0:
            turnover_score = 65
        elif turnover_ratio < 0.5 or turnover_ratio > 5.0:
            turnover_score = 40
        else:
            turnover_score = 50

        return round(volume_score * 0.6 + turnover_score * 0.4, 2)

    def get_momentum_signal(self, kline_data: List[Dict]) -> Dict[str, Any]:
        """获取动量信号分析"""
        if len(kline_data) < 20:
            return {"signal": "neutral", "strength": 0, "reason": "数据不足"}

        ma_score = self._calculate_ma_score(kline_data)
        rsi_score = self._calculate_rsi_score(kline_data)
        price_momentum_score = self._calculate_price_momentum(kline_data)
        volume_momentum_score = self._calculate_volume_momentum(kline_data)

        # 综合信号强度
        overall_score = (
            ma_score * 0.30 +
            rsi_score * 0.25 +
            price_momentum_score * 0.25 +
            volume_momentum_score * 0.20
        )

        # 判断信号
        if overall_score >= 75:
            signal = "strong_buy"
            reason = "动量强劲，建议买入"
        elif overall_score >= 60:
            signal = "buy"
            reason = "动量良好，偏向买入"
        elif overall_score >= 40:
            signal = "neutral"
            reason = "动量中性，观望为主"
        elif overall_score >= 25:
            signal = "sell"
            reason = "动量疲软，偏向卖出"
        else:
            signal = "strong_sell"
            reason = "动量弱势，建议卖出"

        return {
            "signal": signal,
            "strength": overall_score,
            "reason": reason,
            "components": {
                "ma_score": ma_score,
                "rsi_score": rsi_score,
                "price_momentum": price_momentum_score,
                "volume_momentum": volume_momentum_score
            }
        }