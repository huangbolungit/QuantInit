#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stateless Strategy Base - 无状态策略基类
解决状态管理问题的关键组件
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from scripts.bias_free_backtest_engine import (
    SignalGenerator,
    TradingInstruction,
    DataSnapshot
)

class Position:
    """持仓信息数据类"""
    def __init__(self,
                 stock_code: str,
                 quantity: int,
                 entry_price: float,
                 entry_date: str,
                 current_price: float = None,
                 unrealized_pnl: float = None,
                 hold_days: int = 0):
        self.stock_code = stock_code
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.current_price = current_price
        self.unrealized_pnl = unrealized_pnl
        self.hold_days = hold_days

    def update_current_state(self, current_price: float, current_date: str):
        """更新当前状态"""
        self.current_price = current_price
        if self.entry_price > 0:
            self.unrealized_pnl = (current_price - self.entry_price) / self.entry_price

        # 计算持有天数
        entry_dt = datetime.strptime(self.entry_date, '%Y-%m-%d')
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        self.hold_days = (current_dt - entry_dt).days

class PortfolioState:
    """组合状态数据类"""
    def __init__(self,
                 positions: Dict[str, Position] = None,
                 available_cash: float = 1000000.0,
                 portfolio_value: float = 1000000.0):
        self.positions = positions or {}
        self.available_cash = available_cash
        self.portfolio_value = portfolio_value

    def get_position(self, stock_code: str) -> Optional[Position]:
        """获取指定股票的持仓"""
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """检查是否持有指定股票"""
        return stock_code in self.positions

    def update_portfolio_value(self):
        """更新组合总价值"""
        position_value = sum(
            pos.current_price * pos.quantity
            for pos in self.positions.values()
            if pos.current_price is not None
        )
        self.portfolio_value = position_value + self.available_cash

class StatelessStrategyBase(SignalGenerator, ABC):
    """无状态策略基类"""

    def __init__(self, name: str):
        super().__init__(name)
        self._last_portfolio_state = None

    @abstractmethod
    def generate_signals(self,
                         snapshot: DataSnapshot,
                         portfolio_state: PortfolioState) -> List[TradingInstruction]:
        """
        生成交易信号（无状态方法）

        Args:
            snapshot: 当前数据快照
            portfolio_state: 当前组合状态（持仓、现金等）

        Returns:
            交易指令列表
        """
        pass

    def generate_signals_legacy(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """
        兼容旧接口的方法
        如果子类没有重写generate_signals，则使用此方法
        """
        # 创建空的组合状态（向后兼容）
        empty_portfolio = PortfolioState()
        return self.generate_signals(snapshot, empty_portfolio)

class RiskMetrics:
    """风险指标计算工具"""

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate / 252  # 日化无风险利率

        if np.std(excess_returns) == 0:
            return 0.0

        return np.mean(excess_returns) / np.std(excess_returns)

    @staticmethod
    def calculate_max_drawdown(values: List[float]) -> float:
        """计算最大回撤"""
        if not values:
            return 0.0

        peak = values[0]
        max_drawdown = 0.0

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    @staticmethod
    def calculate_calmar_ratio(annual_return: float, max_drawdown: float) -> float:
        """计算卡玛比率"""
        if max_drawdown <= 0:
            return float('inf') if annual_return > 0 else -float('inf')

        return annual_return / max_drawdown

    @staticmethod
    def calculate_sortino_ratio(returns: List[float], target_return: float = 0.0) -> float:
        """计算索提诺比率（下行风险调整收益）"""
        if len(returns) < 2:
            return 0.0

        downside_returns = [r - target_return for r in returns if r < target_return]

        if not downside_returns:
            return float('inf')

        return (np.mean(returns) - target_return) / np.std(downside_returns)

if __name__ == "__main__":
    # 测试无状态策略基类
    print("无状态策略基类创建成功！")
    print("包含的核心组件：")
    print("- Position: 持仓信息数据类")
    print("- PortfolioState: 组合状态数据类")
    print("- StatelessStrategyBase: 无状态策略基类")
    print("- RiskMetrics: 风险指标计算工具")