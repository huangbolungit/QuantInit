#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stateless Strategy Adapter - 无状态策略适配器
将新的无状态策略接口适配到现有的回测引擎
"""

from typing import Dict, List, Any
from datetime import datetime

from scripts.bias_free_backtest_engine import (
    SignalGenerator,
    TradingInstruction,
    DataSnapshot
)
from scripts.stateless_strategy_base import (
    StatelessStrategyBase,
    PortfolioState,
    Position
)

class StatelessStrategyAdapter(SignalGenerator):
    """无状态策略适配器，将新接口适配到旧回测引擎"""

    def __init__(self, stateless_strategy: StatelessStrategyBase):
        super().__init__(stateless_strategy.name)
        self.stateless_strategy = stateless_strategy

        # 内部投资组合状态管理（适配器维护）
        self.portfolio_state = PortfolioState(
            positions={},
            available_cash=1000000.0,
            portfolio_value=1000000.0
        )

        # 记录策略信息
        self.strategy_info = stateless_strategy.get_strategy_info()

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """生成交易信号（适配器方法）"""
        # 更新投资组合状态中的价格信息
        self._update_portfolio_prices(snapshot)

        # 使用新接口生成信号
        return self.stateless_strategy.generate_signals(snapshot, self.portfolio_state)

    def _update_portfolio_prices(self, snapshot: DataSnapshot) -> None:
        """更新投资组合中持仓的当前价格"""
        for stock_code, position in self.portfolio_state.positions.items():
            if stock_code in snapshot.stock_data:
                current_price = float(snapshot.stock_data[stock_code]['close'])
                position.update_current_state(current_price, snapshot.date)

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        base_info = super().get_strategy_info()
        base_info.update(self.strategy_info)
        base_info['adapter_type'] = 'stateless_to_legacy'
        return base_info

    def reset(self) -> None:
        """重置策略状态"""
        self.portfolio_state = PortfolioState(
            positions={},
            available_cash=1000000.0,
            portfolio_value=1000000.0
        )
        # 清理临时状态
        if hasattr(self.stateless_strategy, '_temporary_state'):
            self.stateless_strategy._temporary_state.clear()

    def update_portfolio_after_execution(self,
                                       instruction: TradingInstruction,
                                       success: bool,
                                       execution_price: float = None) -> None:
        """在执行交易后更新投资组合状态"""
        if not success:
            return

        if instruction.action == "buy":
            # 买入成功，添加到投资组合
            position = Position(
                stock_code=instruction.stock_code,
                quantity=instruction.quantity,
                entry_price=execution_price or instruction.price,
                entry_date=instruction.timestamp
            )
            self.portfolio_state.add_position(position)

        elif instruction.action == "sell":
            # 卖出成功，从投资组合移除
            self.portfolio_state.remove_position(instruction.stock_code)

class StatelessMeanReversionStrategy(StatelessStrategyAdapter):
    """兼容的无状态均值回归策略"""

    def __init__(self,
                 lookback_period: int = 10,
                 buy_threshold: float = -0.05,
                 sell_threshold: float = 0.03,
                 stop_loss_threshold: float = 0.08,
                 profit_target: float = 0.10,
                 max_hold_days: int = 15,
                 position_size: int = 1000):

        # 创建内部无状态策略
        from scripts.stateless_mean_reversion_strategy import StatelessMeanReversionStrategy as CoreStrategy
        core_strategy = CoreStrategy(
            lookback_period=lookback_period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            stop_loss_threshold=stop_loss_threshold,
            profit_target=profit_target,
            max_hold_days=max_hold_days,
            position_size=position_size
        )

        super().__init__(core_strategy)
        self.name = f"StatelessMeanReversion_L{lookback_period}_B{buy_threshold}_S{sell_threshold}"

class StatelessMomentumStrategy(StatelessStrategyAdapter):
    """兼容的无状态动量策略"""

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

        # 创建内部无状态策略
        from scripts.stateless_momentum_strategy import StatelessMomentumStrategy as CoreStrategy
        core_strategy = CoreStrategy(
            momentum_period=momentum_period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            stop_loss_threshold=stop_loss_threshold,
            profit_target=profit_target,
            max_hold_days=max_hold_days,
            position_size=position_size,
            volatility_adjustment=volatility_adjustment,
            volume_filter=volume_filter
        )

        super().__init__(core_strategy)
        self.name = f"StatelessMomentum_P{momentum_period}_B{buy_threshold}_S{sell_threshold}"

if __name__ == "__main__":
    # 简单测试
    strategy = StatelessMeanReversionStrategy(
        lookback_period=10,
        buy_threshold=-0.05,
        sell_threshold=0.03,
        stop_loss_threshold=0.08,
        profit_target=0.10,
        max_hold_days=15
    )

    print("无状态策略适配器创建成功！")
    print(f"策略名称: {strategy.name}")
    print(f"策略信息: {strategy.get_strategy_info()}")