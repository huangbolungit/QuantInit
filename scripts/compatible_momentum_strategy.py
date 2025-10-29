#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Compatible Momentum Strategy - 兼容现有框架的动量策略
完全基于OptimizedMeanReversionStrategy模板改造
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import warnings
warnings.filterwarnings('ignore')

from scripts.bias_free_backtest_engine import (
    SignalGenerator,
    TradingInstruction,
    DataSnapshot
)

class CompatibleMomentumStrategy(SignalGenerator):
    """兼容动量策略 - 完全兼容现有参数优化器框架"""

    def __init__(self,
                 momentum_period: int = 10,
                 buy_threshold: float = 0.05,
                 sell_threshold: float = -0.03,
                 max_hold_days: int = 20,
                 position_size: int = 1000):
        super().__init__(f"CompatibleMomentum_P{momentum_period}_B{buy_threshold}_S{sell_threshold}_D{max_hold_days}")

        self.momentum_period = momentum_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.max_hold_days = max_hold_days
        self.position_size = position_size

        # 持仓管理
        self.positions = {}
        self.price_history = {}

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """生成交易信号"""
        instructions = []

        # 更新价格历史
        self._update_price_history(snapshot)

        # 更新持仓
        self._update_positions(snapshot)

        # 检查卖出信号
        sell_instructions = self._check_sell_signals(snapshot)
        instructions.extend(sell_instructions)

        # 检查买入信号
        buy_instructions = self._check_buy_signals(snapshot)
        instructions.extend(buy_instructions)

        return instructions

    def _update_price_history(self, snapshot: DataSnapshot):
        """更新价格历史数据"""
        for stock_code, data in snapshot.stock_data.items():
            if stock_code not in self.price_history:
                self.price_history[stock_code] = []

            # 安全的价格提取
            try:
                close_price = data['close']
                if hasattr(close_price, 'iloc'):
                    # 如果是pandas Series，获取第一个值
                    current_price = float(close_price.iloc[0]) if len(close_price) > 0 else 0.0
                else:
                    current_price = float(close_price)

                if current_price > 0:  # 只记录有效价格
                    self.price_history[stock_code].append({
                        'date': snapshot.date,
                        'price': current_price
                    })

                # 保持固定长度的历史数据
                if len(self.price_history[stock_code]) > self.momentum_period + 5:
                    self.price_history[stock_code] = self.price_history[stock_code][-(self.momentum_period + 5):]

            except (ValueError, TypeError, AttributeError) as e:
                # 跳过无效价格数据
                continue

    def _update_positions(self, snapshot: DataSnapshot):
        """更新持仓信息"""
        for stock_code in list(self.positions.keys()):
            position = self.positions[stock_code]
            entry_date = pd.to_datetime(position['entry_date'])
            current_date = pd.to_datetime(snapshot.date)
            position['hold_days'] = (current_date - entry_date).days

            # 更新当前价格和收益
            if stock_code in snapshot.stock_data:
                try:
                    close_price = snapshot.stock_data[stock_code]['close']
                    if hasattr(close_price, 'iloc'):
                        current_price = float(close_price.iloc[0]) if len(close_price) > 0 else 0.0
                    else:
                        current_price = float(close_price)

                    entry_price = float(position['entry_price'])
                    if current_price > 0 and entry_price > 0:
                        position['current_price'] = current_price
                        position['pnl'] = (current_price - entry_price) / entry_price
                except (ValueError, TypeError, AttributeError):
                    continue

    def _calculate_momentum(self, stock_code: str) -> Optional[float]:
        """计算动量指标"""
        if stock_code not in self.price_history:
            return None

        history = self.price_history[stock_code]
        if len(history) < self.momentum_period + 1:
            return None

        try:
            # 获取历史价格
            current_price = float(history[-1]['price'])
            base_price = float(history[-(self.momentum_period + 1)]['price'])

            if base_price <= 0:
                return None

            # 计算动量 = (当前价格 - 周期前价格) / 周期前价格
            momentum = (current_price - base_price) / base_price
            return float(momentum)
        except (ValueError, TypeError, IndexError):
            return None

    def _check_buy_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查买入信号"""
        instructions = []

        for stock_code in snapshot.stock_data.keys():
            # 跳过已持有的股票
            if stock_code in self.positions:
                continue

            # 计算动量
            momentum = self._calculate_momentum(stock_code)
            if momentum is None:
                continue

            # 动量买入信号：价格涨幅超过买入阈值
            try:
                if momentum >= self.buy_threshold:
                    # 安全的价格提取
                    close_price = snapshot.stock_data[stock_code]['close']
                    if hasattr(close_price, 'iloc'):
                        current_price = float(close_price.iloc[0]) if len(close_price) > 0 else 0.0
                    else:
                        current_price = float(close_price)

                    if current_price <= 0:
                        continue

                    # 创建交易指令
                    instruction = TradingInstruction(
                        stock_code=stock_code,
                        action="buy",
                        quantity=self.position_size,
                        price=current_price,
                        timestamp=snapshot.date,
                        reason=f"动量买入信号：{momentum:.2%} >= {self.buy_threshold:.2%}",
                        confidence=min(float(momentum) / float(self.buy_threshold), 1.0)
                    )

                    instructions.append(instruction)

                    # 记录持仓
                    self.positions[stock_code] = {
                        'entry_price': current_price,
                        'entry_date': snapshot.date,
                        'quantity': self.position_size,
                        'hold_days': 0,
                        'momentum_at_entry': float(momentum)
                    }
            except (ValueError, TypeError, AttributeError):
                continue

        return instructions

    def _check_sell_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查卖出信号"""
        instructions = []

        for stock_code, position in list(self.positions.items()):
            if stock_code not in snapshot.stock_data:
                continue

            try:
                # 安全的价格提取
                close_price = snapshot.stock_data[stock_code]['close']
                if hasattr(close_price, 'iloc'):
                    current_price = float(close_price.iloc[0]) if len(close_price) > 0 else 0.0
                else:
                    current_price = float(close_price)

                if current_price <= 0:
                    continue

                entry_price = float(position['entry_price'])
                if entry_price <= 0:
                    continue

                current_pnl = (current_price - entry_price) / entry_price
                hold_days = position['hold_days']

                sell_reasons = []

                # 1. 止损：动量跌破卖出阈值
                current_momentum = self._calculate_momentum(stock_code)
                if current_momentum is not None and float(current_momentum) <= float(self.sell_threshold):
                    sell_reasons.append(f"动量止损：{current_momentum:.2%} <= {self.sell_threshold:.2%}")

                # 2. 时间止损：持有时间过长
                if hold_days >= self.max_hold_days:
                    sell_reasons.append(f"时间止损：持有{hold_days}天 >= {self.max_hold_days}天")

                # 执行卖出
                if sell_reasons:
                    instruction = TradingInstruction(
                        stock_code=stock_code,
                        action="sell",
                        quantity=position['quantity'],
                        price=current_price,
                        timestamp=snapshot.date,
                        reason=f"动量卖出：{'; '.join(sell_reasons)}",
                        confidence=0.8
                    )

                    instructions.append(instruction)

                    # 移除持仓
                    del self.positions[stock_code]

            except (ValueError, TypeError, AttributeError):
                continue

        return instructions

if __name__ == "__main__":
    # 简单测试
    strategy = CompatibleMomentumStrategy(
        momentum_period=10,
        buy_threshold=0.05,
        sell_threshold=-0.03,
        max_hold_days=20
    )

    print("兼容动量策略创建成功！")
    print(f"策略名称: {strategy.name}")
    print("策略参数:", {
        'momentum_period': strategy.momentum_period,
        'buy_threshold': strategy.buy_threshold,
        'sell_threshold': strategy.sell_threshold,
        'max_hold_days': strategy.max_hold_days
    })