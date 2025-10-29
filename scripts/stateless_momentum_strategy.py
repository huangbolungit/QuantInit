#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stateless Momentum Strategy - 无状态动量策略
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

class StatelessMomentumStrategy(StatelessStrategyBase):
    """无状态动量策略"""

    def __init__(self,
                 momentum_period: int = 10,
                 buy_threshold: float = 0.05,
                 sell_threshold: float = -0.03,
                 stop_loss_threshold: float = 0.08,
                 profit_target: float = 0.15,
                 max_hold_days: int = 20,
                 position_size: int = 1000,
                 volatility_adjustment: bool = True,
                 volume_filter: float = 0.5):
        super().__init__(f"StatelessMomentum_P{momentum_period}_B{buy_threshold}_S{sell_threshold}")

        # 核心策略参数
        self.momentum_period = momentum_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.stop_loss_threshold = stop_loss_threshold
        self.profit_target = profit_target
        self.max_hold_days = max_hold_days
        self.position_size = position_size
        self.volatility_adjustment = volatility_adjustment
        self.volume_filter = volume_filter

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

            # 计算动量信号
            signal = self._calculate_momentum_signal(snapshot, stock_code)
            if signal is None:
                continue

            # 买入信号：动量超过买入阈值
            if signal >= self.buy_threshold:
                current_price = float(snapshot.stock_data[stock_code]['close'])

                # 额外过滤条件
                if not self._pass_buy_filters(snapshot, stock_code, signal):
                    continue

                # 计算置信度
                confidence = self._calculate_buy_confidence(snapshot, stock_code, signal)

                # 创建交易指令
                instruction = TradingInstruction(
                    stock_code=stock_code,
                    action="buy",
                    quantity=self.position_size,
                    price=current_price,
                    timestamp=snapshot.date,
                    reason=f"动量买入：信号{signal:.2%} >= 阈值{self.buy_threshold:.2%}",
                    confidence=confidence
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

            # 3. 动量反转：动量跌破卖出阈值
            momentum_signal = self._calculate_momentum_signal(snapshot, stock_code)
            if momentum_signal is not None and momentum_signal <= self.sell_threshold:
                sell_reasons.append(f"动量反转：信号{momentum_signal:.2%} <= 阈值{self.sell_threshold:.2%}")

            # 4. 时间止损：持有时间过长
            if position.hold_days >= self.max_hold_days:
                sell_reasons.append(f"时间止损：持有{position.hold_days}天 >= {self.max_hold_days}天")

            # 5. 趋势恶化：动量显著转弱
            if self._is_trend_deteriorating(snapshot, stock_code):
                sell_reasons.append("趋势恶化：动量显著转弱")

            # 执行卖出
            if sell_reasons:
                instruction = TradingInstruction(
                    stock_code=stock_code,
                    action="sell",
                    quantity=position.quantity,
                    price=current_price,
                    timestamp=snapshot.date,
                    reason=f"动量卖出：{'; '.join(sell_reasons)}",
                    confidence=0.8
                )

                instructions.append(instruction)

        return instructions

    def _calculate_momentum_signal(self,
                                  snapshot: DataSnapshot,
                                  stock_code: str) -> Optional[float]:
        """计算动量信号"""
        try:
            # 获取历史价格数据
            prices = self._get_price_history(snapshot, stock_code, self.momentum_period + 1)

            if len(prices) < self.momentum_period + 1:
                return None

            # 计算动量：(当前价格 - 周期前价格) / 周期前价格
            current_price = prices[-1]
            base_price = prices[-(self.momentum_period + 1)]

            if base_price == 0:
                return None

            momentum = (current_price - base_price) / base_price

            # 波动率调整
            if self.volatility_adjustment:
                volatility = self._calculate_volatility(prices)
                if volatility > 0:
                    momentum = momentum / volatility  # 风险调整后的动量

            return momentum

        except (ValueError, TypeError, KeyError, IndexError):
            return None

    def _calculate_volatility(self, prices: List[float]) -> float:
        """计算价格波动率"""
        if len(prices) < 2:
            return 0.0

        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns:
            return 0.0

        return np.std(returns) if returns else 0.0

    def _pass_buy_filters(self,
                          snapshot: DataSnapshot,
                          stock_code: str,
                          momentum_signal: float) -> bool:
        """检查买入过滤条件"""
        try:
            stock_data = snapshot.stock_data[stock_code]

            # 成交量过滤：成交量不能太低
            if 'volume' in stock_data:
                avg_volume = self._get_average_volume(snapshot, stock_code)
                current_volume = float(stock_data['volume'])
                if current_volume < avg_volume * self.volume_filter:
                    return False

            # 价格稳定性过滤：价格不能异常波动
            if self.volatility_adjustment:
                prices = self._get_price_history(snapshot, stock_code, self.momentum_period + 1)
                volatility = self._calculate_volatility(prices)
                # 过高波动率的股票可能风险太大
                if volatility > 0.1:  # 10%日波动率阈值
                    return False

            return True

        except (ValueError, TypeError, KeyError):
            return False

    def _calculate_buy_confidence(self,
                                  snapshot: DataSnapshot,
                                  stock_code: str,
                                  momentum_signal: float) -> float:
        """计算买入置信度"""
        base_confidence = min(momentum_signal / self.buy_threshold, 1.0)

        # 基于成交量的调整
        try:
            current_volume = float(snapshot.stock_data[stock_code]['volume'])
            avg_volume = self._get_average_volume(snapshot, stock_code)
            volume_factor = min(current_volume / avg_volume, 2.0) / 2.0  # 归一化到[0,1]

            return base_confidence * (0.7 + 0.3 * volume_factor)
        except:
            return base_confidence * 0.8  # 默认折扣

    def _is_trend_deteriorating(self,
                                snapshot: DataSnapshot,
                                stock_code: str) -> bool:
        """判断趋势是否恶化"""
        try:
            prices = self._get_price_history(snapshot, stock_code, min(self.momentum_period * 2, 20))
            if len(prices) < 5:
                return False

            # 计算短期和长期动量
            short_momentum = (prices[-1] - prices[-min(5, len(prices))]) / prices[-min(5, len(prices))]
            long_momentum = (prices[-1] - prices[0]) / prices[0]

            # 如果短期动量明显低于长期动量，可能趋势恶化
            return short_momentum < long_momentum * 0.5

        except:
            return False

    def _get_price_history(self,
                          snapshot: DataSnapshot,
                          stock_code: str,
                          periods: int) -> List[float]:
        """获取价格历史（模拟实现）"""
        # 在真实环境中，这里应该从历史数据中获取
        # 现在返回一个简单的模拟数据
        try:
            current_price = float(snapshot.stock_data[stock_code]['close'])

            # 模拟历史价格（基于动量特征）
            np.random.seed(hash(stock_code + snapshot.date + str(self.momentum_period)))

            # 生成趋势性价格序列（符合动量策略的特征）
            trend_factor = 1.0 + np.random.normal(0, 0.02, periods)
            prices = []
            base_price = current_price

            for i in range(periods):
                # 从历史价格倒推
                base_price = base_price / trend_factor[periods - 1 - i]
                prices.append(base_price)

            return prices

        except (ValueError, TypeError, KeyError):
            return []

    def _get_average_volume(self,
                            snapshot: DataSnapshot,
                            stock_code: str) -> float:
        """获取平均成交量（模拟实现）"""
        try:
            current_volume = float(snapshot.stock_data[stock_code]['volume'])
            # 模拟平均成交量
            return current_volume * np.random.uniform(0.8, 1.2)
        except:
            return 1000000  # 默认值

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'strategy_name': 'StatelessMomentum',
            'strategy_type': 'momentum',
            'parameters': {
                'momentum_period': self.momentum_period,
                'buy_threshold': self.buy_threshold,
                'sell_threshold': self.sell_threshold,
                'stop_loss_threshold': self.stop_loss_threshold,
                'profit_target': self.profit_target,
                'max_hold_days': self.max_hold_days,
                'position_size': self.position_size,
                'volatility_adjustment': self.volatility_adjustment,
                'volume_filter': self.volume_filter
            },
            'description': f'动量策略 - {self.momentum_period}日动量，买入阈值{self.buy_threshold:.1%}，止损{self.stop_loss_threshold:.1%}',
            'design_pattern': 'stateless',
            'created_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 简单测试
    strategy = StatelessMomentumStrategy(
        momentum_period=10,
        buy_threshold=0.05,
        sell_threshold=-0.03,
        stop_loss_threshold=0.08,
        profit_target=0.15,
        max_hold_days=20,
        volatility_adjustment=True,
        volume_filter=0.5
    )

    print("无状态动量策略创建成功！")
    print(f"策略名称: {strategy.name}")
    print(f"策略信息: {strategy.get_strategy_info()}")