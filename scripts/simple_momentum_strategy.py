#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Momentum Strategy - 简化动量策略
基于现有均值回归策略框架改造
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

class SimpleMomentumStrategy(SignalGenerator):
    """简化动量策略 - 基于均值回归框架改造"""

    def __init__(self,
                 momentum_period: int = 10,
                 buy_threshold: float = 0.05,
                 sell_threshold: float = -0.03,
                 max_hold_days: int = 20,
                 position_size: int = 1000):
        super().__init__(f"SimpleMomentum_P{momentum_period}_B{buy_threshold}_S{sell_threshold}_D{max_hold_days}")

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

            # 添加当前价格
            current_price = float(data['close'])
            self.price_history[stock_code].append({
                'date': snapshot.date,
                'price': current_price
            })

            # 保持固定长度的历史数据
            if len(self.price_history[stock_code]) > self.momentum_period + 5:
                self.price_history[stock_code] = self.price_history[stock_code][-(self.momentum_period + 5):]

    def _update_positions(self, snapshot: DataSnapshot):
        """更新持仓信息"""
        for stock_code in list(self.positions.keys()):
            position = self.positions[stock_code]
            entry_date = pd.to_datetime(position['entry_date'])
            current_date = pd.to_datetime(snapshot.date)
            position['hold_days'] = (current_date - entry_date).days

            # 更新当前价格和收益
            if stock_code in snapshot.stock_data:
                current_price = float(snapshot.stock_data[stock_code]['close'])
                entry_price = float(position['entry_price'])
                position['current_price'] = current_price
                position['pnl'] = (current_price - entry_price) / entry_price

    def _calculate_momentum(self, stock_code: str) -> Optional[float]:
        """计算动量指标"""
        if stock_code not in self.price_history:
            return None

        history = self.price_history[stock_code]
        if len(history) < self.momentum_period + 1:
            return None

        # 获取历史价格
        current_price = float(history[-1]['price'])
        base_price = float(history[-(self.momentum_period + 1)]['price'])

        if base_price <= 0:
            return None

        # 计算动量 = (当前价格 - 周期前价格) / 周期前价格
        momentum = (current_price - base_price) / base_price
        return momentum

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
            if momentum >= self.buy_threshold:
                current_price = float(snapshot.stock_data[stock_code]['close'])

                # 创建交易指令
                instruction = TradingInstruction(
                    stock_code=stock_code,
                    action="buy",
                    quantity=self.position_size,
                    price=current_price,
                    timestamp=snapshot.date,
                    reason=f"动量买入信号：{momentum:.2%} >= {self.buy_threshold:.2%}",
                    confidence=min(momentum / self.buy_threshold, 1.0)
                )

                instructions.append(instruction)

                # 记录持仓
                self.positions[stock_code] = {
                    'entry_price': current_price,
                    'entry_date': snapshot.date,
                    'quantity': self.position_size,
                    'hold_days': 0,
                    'momentum_at_entry': momentum
                }

        return instructions

    def _check_sell_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查卖出信号"""
        instructions = []

        for stock_code, position in list(self.positions.items()):
            if stock_code not in snapshot.stock_data:
                continue

            current_price = float(snapshot.stock_data[stock_code]['close'])
            entry_price = float(position['entry_price'])
            current_pnl = (current_price - entry_price) / entry_price
            hold_days = position['hold_days']

            sell_reasons = []

            # 1. 止损：动量跌破卖出阈值
            current_momentum = self._calculate_momentum(stock_code)
            if current_momentum is not None and current_momentum <= self.sell_threshold:
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

        return instructions

if __name__ == "__main__":
    # 简单测试
    strategy = SimpleMomentumStrategy(
        momentum_period=10,
        buy_threshold=0.05,
        sell_threshold=-0.03,
        max_hold_days=20
    )

    print("简化动量策略创建成功！")
    print(f"策略名称: {strategy.name}")