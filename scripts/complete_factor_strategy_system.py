#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete Factor Strategy System - 完整因子策略系统
包含完整的买入/卖出逻辑和持仓管理
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.bias_free_backtest_engine import (
    BiasFreeBacktestEngine,
    SignalGenerator,
    TradingInstruction,
    DataSnapshot
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """持仓状态"""
    EMPTY = "empty"
    HOLDING = "holding"
    OVERDUE = "overdue"  # 持有时间过长

@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    entry_price: float
    entry_date: str
    quantity: int
    entry_reason: str
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_percentage: float = 0.0
    hold_days: int = 0
    status: PositionStatus = PositionStatus.HOLDING

    def update(self, current_price: float, current_date: str):
        """更新持仓信息"""
        self.current_price = current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        self.pnl_percentage = (current_price - self.entry_price) / self.entry_price * 100

        # 计算持有天数
        entry_dt = pd.to_datetime(self.entry_date)
        current_dt = pd.to_datetime(current_date)
        self.hold_days = (current_dt - entry_dt).days

        # 更新状态
        if self.hold_days > 30:  # 持有超过30天标记为过期
            self.status = PositionStatus.OVERDUE

class CompleteMomentumStrategy(SignalGenerator):
    """完整动量策略 - 包含买入和卖出逻辑"""

    def __init__(self,
                 buy_threshold: float = 0.05,           # 买入阈值：5%涨幅
                 sell_threshold: float = -0.03,        # 卖出阈值：-3%跌幅
                 profit_target: float = 0.08,          # 盈利目标：8%
                 max_hold_days: int = 20,               # 最大持有天数
                 position_size: int = 1000):
        super().__init__(f"CompleteMomentum_B{buy_threshold}_S{sell_threshold}_T{profit_target}_D{max_hold_days}")

        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.profit_target = profit_target
        self.max_hold_days = max_hold_days
        self.position_size = position_size

        # 持仓管理
        self.positions: Dict[str, Position] = {}
        self.portfolio_value = 1000000.0  # 初始资金100万

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """生成交易信号 - 包含买入和卖出逻辑"""
        instructions = []

        # 更新现有持仓
        self._update_positions(snapshot)

        # 检查卖出信号
        sell_instructions = self._check_sell_signals(snapshot)
        instructions.extend(sell_instructions)

        # 检查买入信号
        buy_instructions = self._check_buy_signals(snapshot)
        instructions.extend(buy_instructions)

        return instructions

    def _update_positions(self, snapshot: DataSnapshot):
        """更新所有持仓的当前价格和收益"""
        for stock_code, position in self.positions.items():
            if stock_code in snapshot.stock_data:
                current_price = snapshot.stock_data[stock_code]['close']
                position.update(current_price, snapshot.date)

    def _check_sell_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查卖出信号"""
        instructions = []

        for stock_code, position in list(self.positions.items()):
            sell_reasons = []

            # 1. 止损：动量反转信号
            if stock_code in snapshot.factor_data:
                momentum = snapshot.factor_data[stock_code].get('momentum_score')
                if momentum is not None and momentum < self.sell_threshold:
                    sell_reasons.append(f"Momentum reversal: {momentum:.4f} < {self.sell_threshold}")

            # 2. 止盈：达到盈利目标
            if position.pnl_percentage >= self.profit_target * 100:
                sell_reasons.append(f"Profit target reached: {position.pnl_percentage:.2f}% >= {self.profit_target * 100}%")

            # 3. 时间止损：持有时间过长
            if position.hold_days >= self.max_hold_days:
                sell_reasons.append(f"Max hold days reached: {position.hold_days} >= {self.max_hold_days}")

            # 4. 风险控制：亏损过大
            if position.pnl_percentage <= -0.10:  # 亏损超过10%
                sell_reasons.append(f"Risk control: {position.pnl_percentage:.2f}% <= -10%")

            # 如果有任何卖出理由，执行卖出
            if sell_reasons:
                instructions.append(TradingInstruction(
                    stock_code=stock_code,
                    action='SELL',
                    quantity=position.quantity,
                    reason=f"Sell - {'; '.join(sell_reasons)}",
                    timestamp=snapshot.date
                ))

                logger.info(f"卖出信号: {stock_code}, 原因: {'; '.join(sell_reasons)}, "
                          f"当前收益: {position.pnl_percentage:.2f}%, 持有天数: {position.hold_days}")

        return instructions

    def _check_buy_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查买入信号"""
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            # 跳过已持有的股票
            if stock_code in self.positions:
                continue

            # 检查动量因子
            if 'momentum_score' in factors and not pd.isna(factors['momentum_score']):
                momentum = factors['momentum_score']

                # 买入条件：动量超过阈值
                if momentum > self.buy_threshold:
                    # 风险控制：检查是否有足够的资金
                    if stock_code in snapshot.stock_data:
                        current_price = snapshot.stock_data[stock_code]['close']
                        required_capital = current_price * self.position_size

                        if required_capital < self.portfolio_value * 0.1:  # 单只股票不超过10%资金
                            instructions.append(TradingInstruction(
                                stock_code=stock_code,
                                action='BUY',
                                quantity=self.position_size,
                                reason=f"Buy signal: momentum {momentum:.4f} > {self.buy_threshold}",
                                timestamp=snapshot.date
                            ))

                            logger.info(f"买入信号: {stock_code}, 动量: {momentum:.4f}, 价格: {current_price:.2f}")

        return instructions

    def on_trade_executed(self, instruction: TradingInstruction, execution_price: float, execution_time: str):
        """交易执行回调 - 更新持仓状态"""
        if instruction.action == 'BUY':
            # 添加新持仓
            position = Position(
                stock_code=instruction.stock_code,
                entry_price=execution_price,
                entry_date=execution_time,
                quantity=instruction.quantity,
                entry_reason=instruction.reason
            )
            self.positions[instruction.stock_code] = position

            # 更新资金
            trade_value = execution_price * instruction.quantity
            self.portfolio_value -= trade_value

            logger.info(f"建仓: {instruction.stock_code}, 价格: {execution_price:.2f}, "
                       f"数量: {instruction.quantity}, 原因: {instruction.reason}")

        elif instruction.action == 'SELL':
            # 移除持仓
            if instruction.stock_code in self.positions:
                position = self.positions.pop(instruction.stock_code)

                # 计算收益
                trade_value = execution_price * instruction.quantity
                pnl = (execution_price - position.entry_price) * instruction.quantity
                pnl_percentage = (execution_price - position.entry_price) / position.entry_price * 100

                # 更新资金
                self.portfolio_value += trade_value

                logger.info(f"平仓: {instruction.stock_code}, 入场价: {position.entry_price:.2f}, "
                           f"出场价: {execution_price:.2f}, 收益: {pnl:.2f} ({pnl_percentage:.2f}%), "
                           f"持有天数: {position.hold_days}")

    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计信息"""
        if not self.positions:
            return {
                "total_positions": 0,
                "total_pnl": 0.0,
                "portfolio_value": self.portfolio_value,
                "cash_ratio": 1.0
            }

        total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_positions_value = sum(pos.current_price * pos.quantity for pos in self.positions.values())

        return {
            "total_positions": len(self.positions),
            "total_unrealized_pnl": total_pnl,
            "total_positions_value": total_positions_value,
            "portfolio_value": self.portfolio_value + total_positions_value,
            "cash_ratio": self.portfolio_value / (self.portfolio_value + total_positions_value),
            "positions": [
                {
                    "stock_code": pos.stock_code,
                    "pnl_percentage": pos.pnl_percentage,
                    "hold_days": pos.hold_days,
                    "status": pos.status.value
                }
                for pos in self.positions.values()
            ]
        }

class CompleteStrategyBacktester:
    """完整策略回测器"""

    def __init__(self, data_dir: str = "data/historical/stocks/complete_csi800/stocks"):
        self.data_dir = Path(data_dir)
        self.results_dir = Path("complete_strategy_results")
        self.results_dir.mkdir(exist_ok=True)

    def run_strategy_test(self, strategy: SignalGenerator, stock_codes: List[str],
                          start_date: str, end_date: str) -> Dict[str, Any]:
        """运行策略测试"""
        logger.info(f"开始测试策略: {strategy.name}")
        logger.info(f"股票数量: {len(stock_codes)}, 测试期间: {start_date} 到 {end_date}")

        # 创建自定义回测引擎
        class StrategyBacktestEngine(BiasFreeBacktestEngine):
            def __init__(self, backtester, strategy):
                super().__init__()
                self.backtester = backtester
                self.strategy = strategy
                self.strategy_stats = []

            def create_data_snapshot(self, date, stock_data):
                basic_snapshot = super().create_data_snapshot(date, stock_data)
                enhanced_snapshot = self.backtester.enhance_with_factors(basic_snapshot)
                return enhanced_snapshot

            def on_trade_executed(self, instruction: TradingInstruction, execution_price: float, execution_time: str):
                super().on_trade_executed(instruction, execution_price, execution_time)

                # 调用策略的回调
                if hasattr(self.strategy, 'on_trade_executed'):
                    self.strategy.on_trade_executed(instruction, execution_price, execution_time)

            def record_daily_stats(self, date, portfolio_value, positions):
                # 记录每日策略统计
                if hasattr(self.strategy, 'get_strategy_stats'):
                    stats = self.strategy.get_strategy_stats()
                    stats['date'] = date
                    stats['portfolio_value'] = portfolio_value
                    self.strategy_stats.append(stats)

        # 创建并运行回测
        backtest_engine = StrategyBacktestEngine(self, strategy)
        backtest_engine.add_signal_generator(strategy)

        results = backtest_engine.run_bias_free_backtest(stock_codes, start_date, end_date)

        # 添加策略特定的统计信息
        results['strategy_daily_stats'] = getattr(backtest_engine, 'strategy_stats', [])
        results['final_strategy_stats'] = strategy.get_strategy_stats() if hasattr(strategy, 'get_strategy_stats') else {}

        return results

    def enhance_with_factors(self, snapshot: DataSnapshot) -> DataSnapshot:
        """为数据快照添加因子数据"""
        enhanced_factor_data = {}

        for stock_code, stock_data in snapshot.stock_data.items():
            enhanced_factor_data[stock_code] = {}

            # 获取历史数据计算因子
            data = self._load_stock_historical_data(stock_code, snapshot.date)
            if data is None or len(data) < 30:
                continue

            # 计算动量因子
            momentum = CompleteStrategyBacktester.calculate_momentum(data, 20)
            if not pd.isna(momentum):
                enhanced_factor_data[stock_code]['momentum_score'] = momentum

        return DataSnapshot(
            date=snapshot.date,
            stock_data=snapshot.stock_data,
            market_data=snapshot.market_data,
            factor_data=enhanced_factor_data,
            is_valid=snapshot.is_valid
        )

    def _load_stock_historical_data(self, stock_code: str, current_date: str) -> pd.DataFrame:
        """加载个股历史数据"""
        try:
            if isinstance(current_date, str):
                year = current_date.split('-')[0]
                current_dt = pd.to_datetime(current_date)
            else:
                year = str(current_date.year)
                current_dt = current_date

            file_path = self.data_dir / year / f"{stock_code}.csv"

            if file_path.exists():
                data = pd.read_csv(file_path)
                data['date'] = pd.to_datetime(data['date'])

                historical_data = data[data['date'] <= current_dt].copy()
                return historical_data
        except Exception as e:
            logger.warning(f"加载 {stock_code} 历史数据失败: {e}")

        return None

    @staticmethod
    def calculate_momentum(data: pd.DataFrame, lookback_period: int = 20) -> float:
        """计算动量因子"""
        if len(data) < lookback_period + 1:
            return np.nan

        start_price = data['close'].iloc[-(lookback_period + 1)]
        end_price = data['close'].iloc[-1]

        momentum = (end_price - start_price) / start_price
        return momentum

def run_multiple_strategy_tests():
    """运行多个策略测试"""

    # 创建回测器
    backtester = CompleteStrategyBacktester()

    # 定义测试参数
    stock_codes = ['000001', '000002', '600036', '600519', '000858']  # 测试股票组合
    start_date = '2022-01-01'
    end_date = '2023-12-31'

    # 定义不同的策略参数组合
    strategies = [
        CompleteMomentumStrategy(buy_threshold=0.03, sell_threshold=-0.02, profit_target=0.06, max_hold_days=15),
        CompleteMomentumStrategy(buy_threshold=0.05, sell_threshold=-0.03, profit_target=0.08, max_hold_days=20),
        CompleteMomentumStrategy(buy_threshold=0.08, sell_threshold=-0.05, profit_target=0.12, max_hold_days=25),
        CompleteMomentumStrategy(buy_threshold=0.05, sell_threshold=-0.02, profit_target=0.10, max_hold_days=30),
    ]

    logger.info(f"开始运行 {len(strategies)} 个策略测试...")

    results = {}

    for i, strategy in enumerate(strategies, 1):
        logger.info(f"\n=== 测试策略 {i}/{len(strategies)}: {strategy.name} ===")

        try:
            result = backtester.run_strategy_test(strategy, stock_codes, start_date, end_date)
            results[strategy.name] = result

            # 保存单个策略结果
            result_file = backtester.results_dir / f"{strategy.name}_results.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)

            # 输出简要结果
            total_return = result.get('total_return', 0)
            sharpe_ratio = result.get('sharpe_ratio', 0)
            max_drawdown = result.get('max_drawdown', 0)
            trade_count = len(result.get('trades', []))

            logger.info(f"策略 {strategy.name} 结果:")
            logger.info(f"  总收益: {total_return:.2f}%")
            logger.info(f"  夏普比率: {sharpe_ratio:.2f}")
            logger.info(f"  最大回撤: {max_drawdown:.2f}%")
            logger.info(f"  交易次数: {trade_count}")
            logger.info(f"  结果已保存到: {result_file}")

        except Exception as e:
            logger.error(f"策略 {strategy.name} 测试失败: {e}")
            results[strategy.name] = {"error": str(e)}

    # 生成综合报告
    generate_comprehensive_report(results, backtester.results_dir)

    return results

def generate_comprehensive_report(results: Dict[str, Any], results_dir: Path):
    """生成综合报告"""
    report_lines = []
    report_lines.append("# Complete Factor Strategy System - 完整因子策略系统报告")
    report_lines.append("=" * 80)
    report_lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**测试策略数量**: {len(results)}")
    report_lines.append("")

    # 策略性能排名
    strategy_performance = []

    for strategy_name, result in results.items():
        if "error" not in result:
            performance = result.get('total_return', 0)
            sharpe = result.get('sharpe_ratio', 0)
            max_dd = result.get('max_drawdown', 0)
            trade_count = len(result.get('trades', []))

            strategy_performance.append({
                'name': strategy_name,
                'return': performance,
                'sharpe': sharpe,
                'max_dd': max_dd,
                'trades': trade_count
            })

    # 按收益排序
    strategy_performance.sort(key=lambda x: x['return'], reverse=True)

    report_lines.append("## 📊 策略性能排名")
    report_lines.append("")
    report_lines.append("| 排名 | 策略名称 | 总收益 | 夏普比率 | 最大回撤 | 交易次数 |")
    report_lines.append("|------|----------|--------|----------|----------|----------|")

    for i, strategy in enumerate(strategy_performance, 1):
        status = "✅" if strategy['return'] > 0 else "❌"
        report_lines.append(f"| {i} | {strategy['name']} | {strategy['return']:.2f}% | "
                          f"{strategy['sharpe']:.2f} | {strategy['max_dd']:.2f}% | "
                          f"{strategy['trades']} | {status}")

    report_lines.append("")

    # 找出有效策略
    profitable_strategies = [s for s in strategy_performance if s['return'] > 0]

    report_lines.append("## 🎯 关键发现")
    report_lines.append("")

    if profitable_strategies:
        report_lines.append(f"### ✅ 找到 {len(profitable_strategies)} 个有效策略")
        report_lines.append("")

        best_strategy = profitable_strategies[0]
        report_lines.append(f"**最佳策略**: {best_strategy['name']}")
        report_lines.append(f"- 总收益: {best_strategy['return']:.2f}%")
        report_lines.append(f"- 夏普比率: {best_strategy['sharpe']:.2f}")
        report_lines.append(f"- 最大回撤: {best_strategy['max_dd']:.2f}%")
        report_lines.append(f"- 交易次数: {best_strategy['trades']}")
        report_lines.append("")

        report_lines.append("### 📈 有效策略列表")
        for strategy in profitable_strategies:
            report_lines.append(f"- **{strategy['name']}**: {strategy['return']:.2f}% 收益, "
                              f"{strategy['trades']} 次交易")
    else:
        report_lines.append("### ❌ 未找到有效策略")
        report_lines.append("所有策略在测试期间都未能产生正收益。")
        report_lines.append("")
        report_lines.append("#### 可能的原因:")
        report_lines.append("1. 市场环境不适合动量策略")
        report_lines.append("2. 买入/卖出阈值设置过于保守")
        report_lines.append("3. 交易成本过高")
        report_lines.append("4. 需要更复杂的策略组合")

    report_lines.append("")
    report_lines.append("## 🔧 策略改进建议")
    report_lines.append("")
    report_lines.append("### 参数优化方向")
    report_lines.append("1. **买入阈值**: 尝试更低的买入阈值以增加交易频率")
    report_lines.append("2. **卖出阈值**: 调整卖出时机以优化收益")
    report_lines.append("3. **持仓时间**: 优化最大持有天数以平衡收益和风险")
    report_lines.append("4. **仓位管理**: 实施动态仓位调整策略")
    report_lines.append("")

    report_lines.append("### 策略组合建议")
    report_lines.append("1. **多因子融合**: 结合动量、均值回归、波动率等因子")
    report_lines.append("2. **市场环境适应**: 牛市/熊市使用不同参数")
    report_lines.append("3. **风险管理**: 增加止损和资金管理机制")
    report_lines.append("4. **成本优化**: 降低交易频率以减少成本")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("*基于完整买入/卖出逻辑的策略回测系统*")

    # 保存报告
    report_file = results_dir / "complete_strategy_system_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"综合报告已保存到: {report_file}")

    return profitable_strategies

def main():
    """主函数"""
    logger.info("🚀 启动完整因子策略系统测试")
    logger.info("=" * 60)

    # 运行多策略测试
    results = run_multiple_strategy_tests()

    # 统计结果
    successful_tests = len([r for r in results.values() if "error" not in r])
    profitable_strategies = len([r for r in results.values()
                               if "error" not in r and r.get('total_return', 0) > 0])

    logger.info("\n" + "=" * 60)
    logger.info("📊 测试总结")
    logger.info(f"成功测试: {successful_tests}/{len(results)}")
    logger.info(f"有效策略: {profitable_strategies}/{successful_tests}")

    if profitable_strategies > 0:
        logger.info("🎉 成功找到有效策略！")
        logger.info("查看详细报告了解策略表现和改进建议。")
    else:
        logger.info("⚠️ 未找到有效策略，建议调整策略参数或尝试其他因子组合。")

    logger.info("=" * 60)

if __name__ == "__main__":
    main()