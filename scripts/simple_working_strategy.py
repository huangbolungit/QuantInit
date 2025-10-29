#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Working Strategy - 简单有效的策略原型
专注于创建一个能产生正收益的基本策略
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional
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

class SimpleMeanReversionStrategy(SignalGenerator):
    """简单均值回归策略 - 买入低点，卖出高点"""

    def __init__(self,
                 lookback_period: int = 10,
                 buy_threshold: float = -0.05,    # 低于均线5%时买入
                 sell_threshold: float = 0.03,    # 高于均线3%时卖出
                 max_hold_days: int = 15,
                 position_size: int = 1000):
        super().__init__(f"SimpleMeanReversion_L{lookback_period}_B{buy_threshold}_S{sell_threshold}")
        self.lookback_period = lookback_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.max_hold_days = max_hold_days
        self.position_size = position_size

        # 持仓管理
        self.positions = {}  # stock_code -> {'entry_price': float, 'entry_date': str, 'quantity': int}

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """生成交易信号"""
        instructions = []

        # 更新持仓信息
        self._update_positions(snapshot)

        # 检查卖出信号
        sell_instructions = self._check_sell_signals(snapshot)
        instructions.extend(sell_instructions)

        # 检查买入信号
        buy_instructions = self._check_buy_signals(snapshot)
        instructions.extend(buy_instructions)

        return instructions

    def _update_positions(self, snapshot: DataSnapshot):
        """更新持仓信息（计算持有天数）"""
        for stock_code in list(self.positions.keys()):
            position = self.positions[stock_code]
            entry_date = pd.to_datetime(position['entry_date'])
            current_date = pd.to_datetime(snapshot.date)
            position['hold_days'] = (current_date - entry_date).days

    def _check_sell_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查卖出信号"""
        instructions = []

        for stock_code, position in list(self.positions.items()):
            sell_reasons = []

            # 1. 价格回归均值：超过卖出阈值
            if stock_code in snapshot.stock_data:
                current_price = snapshot.stock_data[stock_code]['close']
                entry_price = position['entry_price']
                price_change = (current_price - entry_price) / entry_price

                if price_change >= self.sell_threshold:
                    sell_reasons.append(f"Price target: {price_change:.4f} >= {self.sell_threshold}")

            # 2. 时间止损：持有时间过长
            if position.get('hold_days', 0) >= self.max_hold_days:
                sell_reasons.append(f"Max hold days: {position['hold_days']} >= {self.max_hold_days}")

            # 3. 风险控制：亏损过大
            if stock_code in snapshot.stock_data:
                current_price = snapshot.stock_data[stock_code]['close']
                entry_price = position['entry_price']
                price_change = (current_price - entry_price) / entry_price

                if price_change <= -0.08:  # 亏损超过8%
                    sell_reasons.append(f"Risk control: {price_change:.4f} <= -0.08")

            # 执行卖出
            if sell_reasons:
                instructions.append(TradingInstruction(
                    stock_code=stock_code,
                    action='SELL',
                    quantity=position['quantity'],
                    reason=f"Sell - {'; '.join(sell_reasons)}",
                    timestamp=snapshot.date
                ))

                logger.info(f"卖出信号: {stock_code}, 原因: {'; '.join(sell_reasons)}")

        return instructions

    def _check_buy_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查买入信号"""
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            # 跳过已持有的股票
            if stock_code in self.positions:
                continue

            # 检查均值回归因子
            if 'mean_reversion_score' in factors and not pd.isna(factors['mean_reversion_score']):
                reversion_score = factors['mean_reversion_score']

                # 买入条件：价格显著低于均值
                if reversion_score <= self.buy_threshold:
                    if stock_code in snapshot.stock_data:
                        current_price = snapshot.stock_data[stock_code]['close']

                        instructions.append(TradingInstruction(
                            stock_code=stock_code,
                            action='BUY',
                            quantity=self.position_size,
                            reason=f"Buy signal: mean reversion {reversion_score:.4f} <= {self.buy_threshold}",
                            timestamp=snapshot.date
                        ))

                        logger.info(f"买入信号: {stock_code}, 均值回归得分: {reversion_score:.4f}, 价格: {current_price:.2f}")

        return instructions

    def on_trade_executed(self, instruction: TradingInstruction, execution_price: float, execution_time: str):
        """交易执行回调"""
        if instruction.action == 'BUY':
            # 添加新持仓
            self.positions[instruction.stock_code] = {
                'entry_price': execution_price,
                'entry_date': execution_time,
                'quantity': instruction.quantity,
                'hold_days': 0
            }

            pnl = 0.0
            logger.info(f"建仓: {instruction.stock_code}, 价格: {execution_price:.2f}, 数量: {instruction.quantity}")

        elif instruction.action == 'SELL':
            # 移除持仓并计算收益
            if instruction.stock_code in self.positions:
                position = self.positions.pop(instruction.stock_code)
                entry_price = position['entry_price']
                pnl = (execution_price - entry_price) * instruction.quantity
                pnl_percentage = (execution_price - entry_price) / entry_price * 100

                logger.info(f"平仓: {instruction.stock_code}, 入场: {entry_price:.2f}, 出场: {execution_price:.2f}, "
                           f"收益: {pnl:.2f} ({pnl_percentage:.2f}%), 持有天数: {position.get('hold_days', 0)}")

    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        return {
            "current_positions": len(self.positions),
            "positions": list(self.positions.keys())
        }

class SimpleStrategyBacktester:
    """简单策略回测器"""

    def __init__(self, data_dir: str = "data/historical/stocks/complete_csi800/stocks"):
        self.data_dir = Path(data_dir)
        self.results_dir = Path("simple_strategy_results")
        self.results_dir.mkdir(exist_ok=True)

    def run_strategy_test(self, strategy: SignalGenerator, stock_codes: List[str],
                          start_date: str, end_date: str) -> Dict[str, Any]:
        """运行策略测试"""
        logger.info(f"测试策略: {strategy.name}")
        logger.info(f"股票: {stock_codes}, 期间: {start_date} 到 {end_date}")

        # 创建自定义回测引擎
        class SimpleBacktestEngine(BiasFreeBacktestEngine):
            def __init__(self, backtester, strategy):
                super().__init__()
                self.backtester = backtester
                self.strategy = strategy

            def create_data_snapshot(self, date, stock_data):
                basic_snapshot = super().create_data_snapshot(date, stock_data)
                enhanced_snapshot = self.backtester.enhance_with_factors(basic_snapshot)
                return enhanced_snapshot

            def on_trade_executed(self, instruction: TradingInstruction, execution_price: float, execution_time: str):
                super().on_trade_executed(instruction, execution_price, execution_time)
                if hasattr(self.strategy, 'on_trade_executed'):
                    self.strategy.on_trade_executed(instruction, execution_price, execution_time)

        # 创建并运行回测
        backtest_engine = SimpleBacktestEngine(self, strategy)
        backtest_engine.add_signal_generator(strategy)

        results = backtest_engine.run_bias_free_backtest(stock_codes, start_date, end_date)

        # 添加策略统计
        if hasattr(strategy, 'get_strategy_stats'):
            results['final_strategy_stats'] = strategy.get_strategy_stats()

        return results

    def enhance_with_factors(self, snapshot: DataSnapshot) -> DataSnapshot:
        """添加因子数据"""
        enhanced_factor_data = {}

        for stock_code, stock_data in snapshot.stock_data.items():
            enhanced_factor_data[stock_code] = {}

            # 获取历史数据
            data = self._load_stock_historical_data(stock_code, snapshot.date)
            if data is None or len(data) < 20:
                continue

            # 计算均值回归因子
            reversion_score = self.calculate_mean_reversion(data, 10)
            if not pd.isna(reversion_score):
                enhanced_factor_data[stock_code]['mean_reversion_score'] = reversion_score

        return DataSnapshot(
            date=snapshot.date,
            stock_data=snapshot.stock_data,
            market_data=snapshot.market_data,
            factor_data=enhanced_factor_data,
            is_valid=snapshot.is_valid
        )

    def _load_stock_historical_data(self, stock_code: str, current_date: str) -> pd.DataFrame:
        """加载历史数据"""
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

    def calculate_mean_reversion(self, data: pd.DataFrame, lookback_period: int = 10) -> float:
        """计算均值回归因子"""
        if len(data) < lookback_period + 1:
            return np.nan

        recent_prices = data['close'].iloc[-lookback_period:]
        current_price = data['close'].iloc[-1]
        mean_price = recent_prices.mean()

        if mean_price > 0:
            # 计算相对于均值的偏离
            deviation = (current_price - mean_price) / mean_price
            return deviation

        return np.nan

def run_simple_strategy_test():
    """运行简单策略测试"""
    logger.info("🚀 启动简单策略测试")
    logger.info("=" * 50)

    # 创建回测器
    backtester = SimpleStrategyBacktester()

    # 测试参数
    stock_codes = ['000001', '000002', '600036', '600519', '000858']
    start_date = '2022-01-01'
    end_date = '2023-12-31'

    # 定义不同参数的策略
    strategies = [
        SimpleMeanReversionStrategy(lookback_period=5, buy_threshold=-0.03, sell_threshold=0.02, max_hold_days=10),
        SimpleMeanReversionStrategy(lookback_period=10, buy_threshold=-0.05, sell_threshold=0.03, max_hold_days=15),
        SimpleMeanReversionStrategy(lookback_period=15, buy_threshold=-0.08, sell_threshold=0.05, max_hold_days=20),
        SimpleMeanReversionStrategy(lookback_period=20, buy_threshold=-0.10, sell_threshold=0.06, max_hold_days=25),
    ]

    results = {}

    for i, strategy in enumerate(strategies, 1):
        logger.info(f"\n--- 测试策略 {i}/{len(strategies)}: {strategy.name} ---")

        try:
            result = backtester.run_strategy_test(strategy, stock_codes, start_date, end_date)
            results[strategy.name] = result

            # 输出结果
            total_return = result.get('total_return', 0)
            sharpe_ratio = result.get('sharpe_ratio', 0)
            max_drawdown = result.get('max_drawdown', 0)
            trade_count = len(result.get('trades', []))

            logger.info(f"策略 {strategy.name} 结果:")
            logger.info(f"  总收益: {total_return:.2f}%")
            logger.info(f"  夏普比率: {sharpe_ratio:.2f}")
            logger.info(f"  最大回撤: {max_drawdown:.2f}%")
            logger.info(f"  交易次数: {trade_count}")

            # 保存结果
            result_file = backtester.results_dir / f"{strategy.name}_results.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            logger.error(f"策略 {strategy.name} 测试失败: {e}")
            results[strategy.name] = {"error": str(e)}

    # 生成报告
    generate_report(results, backtester.results_dir)

    return results

def generate_report(results: Dict[str, Any], results_dir: Path):
    """生成报告"""
    report_lines = []
    report_lines.append("# Simple Strategy Test Report - 简单策略测试报告")
    report_lines.append("=" * 60)
    report_lines.append(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**测试策略数量**: {len(results)}")
    report_lines.append("")

    # 策略性能
    strategy_performance = []

    for strategy_name, result in results.items():
        if "error" not in result:
            performance = result.get('total_return', 0)
            sharpe = result.get('sharpe_ratio', 0)
            max_dd = result.get('max_drawdown', 0)
            trades = len(result.get('trades', []))

            strategy_performance.append({
                'name': strategy_name,
                'return': performance,
                'sharpe': sharpe,
                'max_dd': max_dd,
                'trades': trades
            })

    strategy_performance.sort(key=lambda x: x['return'], reverse=True)

    report_lines.append("## 📊 策略性能排名")
    report_lines.append("")
    report_lines.append("| 排名 | 策略名称 | 总收益 | 夏普比率 | 最大回撤 | 交易次数 | 状态 |")
    report_lines.append("|------|----------|--------|----------|----------|----------|------|")

    for i, strategy in enumerate(strategy_performance, 1):
        status = "✅ 有效" if strategy['return'] > 0 else "❌ 无效"
        report_lines.append(f"| {i} | {strategy['name'][:30]} | {strategy['return']:.2f}% | "
                          f"{strategy['sharpe']:.2f} | {strategy['max_dd']:.2f}% | "
                          f"{strategy['trades']} | {status} |")

    report_lines.append("")

    # 关键发现
    profitable_strategies = [s for s in strategy_performance if s['return'] > 0]

    report_lines.append("## 🎯 关键发现")
    report_lines.append("")

    if profitable_strategies:
        report_lines.append(f"### ✅ 找到 {len(profitable_strategies)} 个有效策略")
        best = profitable_strategies[0]
        report_lines.append(f"**最佳策略**: {best['name']}")
        report_lines.append(f"- 总收益: {best['return']:.2f}%")
        report_lines.append(f"- 夏普比率: {best['sharpe']:.2f}")
        report_lines.append(f"- 交易次数: {best['trades']}")
    else:
        report_lines.append("### ❌ 未找到有效策略")
        report_lines.append("所有策略都未能产生正收益。")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    # 保存报告
    report_file = results_dir / "simple_strategy_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    logger.info(f"报告已保存到: {report_file}")

    return profitable_strategies

def main():
    """主函数"""
    results = run_simple_strategy_test()

    # 统计
    successful = len([r for r in results.values() if "error" not in r])
    profitable = len([r for r in results.values() if "error" not in r and r.get('total_return', 0) > 0])

    logger.info("\n" + "=" * 50)
    logger.info("📊 测试总结")
    logger.info(f"成功测试: {successful}/{len(results)}")
    logger.info(f"有效策略: {profitable}/{successful}")

    if profitable > 0:
        logger.info("🎉 成功找到有效策略！")
    else:
        logger.info("⚠️ 未找到有效策略，建议继续优化。")

if __name__ == "__main__":
    main()