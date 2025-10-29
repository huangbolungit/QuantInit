#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stateless Mean Reversion Strategy - 无状态均值回归策略
完全解决状态管理问题的重构版本
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import warnings
warnings.filterwarnings('ignore')

from scripts.stateless_strategy_base import (
    StatelessStrategyBase,
    TradingInstruction,
    DataSnapshot,
    PortfolioState,
    Position,
    RiskMetrics
)

class StatelessMeanReversionStrategy(StatelessStrategyBase):
    """无状态均值回归策略"""

    def __init__(self,
                 lookback_period: int = 10,
                 buy_threshold: float = -0.05,
                 sell_threshold: float = 0.03,
                 stop_loss_threshold: float = 0.08,
                 profit_target: float = 0.10,
                 max_hold_days: int = 15,
                 position_size: int = 1000):
        super().__init__(f"StatelessMeanReversion_L{lookback_period}_B{buy_threshold}_S{sell_threshold}")

        # 核心策略参数
        self.lookback_period = lookback_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.stop_loss_threshold = stop_loss_threshold
        self.profit_target = profit_target
        self.max_hold_days = max_hold_days
        self.position_size = position_size

        # 内部状态（仅用于临时计算，不持久化）
        self._temporary_state = {}

    def generate_signals(self,
                         snapshot: DataSnapshot,
                         portfolio_state: PortfolioState) -> List[TradingInstruction]:
        """生成交易信号（无状态方法）"""
        instructions = []

        # 生成买入信号
        buy_instructions = self._generate_buy_signals(snapshot, portfolio_state)
        instructions.extend(buy_instructions)

        # 生成卖出信号
        sell_instructions = self._generate_sell_signals(snapshot, portfolio_state)
        instructions.extend(sell_instructions)

        return instructions

    def _generate_buy_signals(self,
                             snapshot: DataSnapshot,
                             portfolio_state: PortfolioState) -> List[TradingInstruction]:
        """生成买入信号"""
        instructions = []

        for stock_code in snapshot.stock_data.keys():
            # 跳过已持有的股票
            if portfolio_state.has_position(stock_code):
                continue

            # 计算均值回归信号
            signal = self._calculate_mean_reversion_signal(snapshot, stock_code)
            if signal is None:
                continue

            # 买入信号：价格低于均值一定幅度
            if signal <= self.buy_threshold:
                current_price = float(snapshot.stock_data[stock_code]['close'])

                # 创建交易指令
                instruction = TradingInstruction(
                    stock_code=stock_code,
                    action="buy",
                    quantity=self.position_size,
                    price=current_price,
                    timestamp=snapshot.date,
                    reason=f"均值回归买入：信号{signal:.2%} <= 阈值{self.buy_threshold:.2%}",
                    confidence=min(abs(signal) / abs(self.buy_threshold), 1.0)
                )

                instructions.append(instruction)

        return instructions

    def _generate_sell_signals(self,
                              snapshot: DataSnapshot,
                              portfolio_state: PortfolioState) -> List[TradingInstruction]:
        """生成卖出信号"""
        instructions = []

        for stock_code, position in portfolio_state.positions.items():
            if stock_code not in snapshot.stock_data:
                continue

            current_price = float(snapshot.stock_data[stock_code]['close'])

            # 更新持仓信息
            position.update_current_state(current_price, snapshot.date)

            # 检查卖出条件
            sell_reasons = []

            # 1. 止盈：达到盈利目标
            if position.unrealized_pnl >= self.profit_target:
                sell_reasons.append(f"止盈：{position.unrealized_pnl:.2%} >= {self.profit_target:.2%}")

            # 2. 止损：超过止损阈值
            if position.unrealized_pnl <= -self.stop_loss_threshold:
                sell_reasons.append(f"止损：{position.unrealized_pnl:.2%} <= -{self.stop_loss_threshold:.2%}")

            # 3. 止盈：达到卖出阈值
            mean_signal = self._calculate_mean_reversion_signal(snapshot, stock_code)
            if mean_signal is not None and mean_signal >= self.sell_threshold:
                sell_reasons.append(f"均值回归卖出：信号{mean_signal:.2%} >= 阈值{self.sell_threshold:.2%}")

            # 4. 时间止损：持有时间过长
            if position.hold_days >= self.max_hold_days:
                sell_reasons.append(f"时间止损：持有{position.hold_days}天 >= {self.max_hold_days}天")

            # 执行卖出
            if sell_reasons:
                instruction = TradingInstruction(
                    stock_code=stock_code,
                    action="sell",
                    quantity=position.quantity,
                    price=current_price,
                    timestamp=snapshot.date,
                    reason=f"均值回归卖出：{'; '.join(sell_reasons)}",
                    confidence=0.8
                )

                instructions.append(instruction)

        return instructions

    def _calculate_mean_reversion_signal(self,
                                        snapshot: DataSnapshot,
                                        stock_code: str) -> Optional[float]:
        """计算均值回归信号"""
        try:
            # 获取历史价格数据
            prices = self._get_price_history(snapshot, stock_code, self.lookback_period + 1)

            if len(prices) < self.lookback_period + 1:
                return None

            # 计算均值
            mean_price = np.mean(prices[:-1])  # 排除当前价格
            current_price = prices[-1]

            if mean_price == 0:
                return None

            # 计算均值回归信号：(当前价格 - 均值) / 均值
            signal = (current_price - mean_price) / mean_price
            return signal

        except (ValueError, TypeError, KeyError, IndexError):
            return None

    def _get_price_history(self,
                          snapshot: DataSnapshot,
                          stock_code: str,
                          periods: int) -> List[float]:
        """获取价格历史（模拟实现）"""
        # 在真实环境中，这里应该从历史数据中获取
        # 现在返回一个简单的模拟数据
        try:
            current_price = float(snapshot.stock_data[stock_code]['close'])

            # 模拟历史价格（围绕当前价格的小幅波动）
            np.random.seed(hash(stock_code + snapshot.date))  # 确保可重现性
            noise = np.random.normal(0, 0.02, periods)
            prices = [current_price * (1 + n) for n in noise]

            return prices
        except (ValueError, TypeError, KeyError):
            return []

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'strategy_name': 'StatelessMeanReversion',
            'strategy_type': 'mean_reversion',
            'parameters': {
                'lookback_period': self.lookback_period,
                'buy_threshold': self.buy_threshold,
                'sell_threshold': self.sell_threshold,
                'stop_loss_threshold': self.stop_loss_threshold,
                'profit_target': self.profit_target,
                'max_hold_days': self.max_hold_days,
                'position_size': self.position_size
            },
            'description': f'均值回归策略 - {self.lookback_period}日均值，买入阈值{self.buy_threshold:.1%}，止损{self.stop_loss_threshold:.1%}',
            'design_pattern': 'stateless',
            'created_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 简单测试
    strategy = StatelessMeanReversionStrategy(
        lookback_period=10,
        buy_threshold=-0.08,
        sell_threshold=0.02,
        stop_loss_threshold=0.10,
        profit_target=0.12,
        max_hold_days=20
    )

    print("无状态均值回归策略创建成功！")
    print(f"策略名称: {strategy.name}")
    print(f"策略信息: {strategy.get_strategy_info()}")