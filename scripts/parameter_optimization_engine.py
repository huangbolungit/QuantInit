#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parameter Optimization Engine - 参数优化引擎
基于现有策略框架进行系统性的参数优化测试
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path
import logging
from typing import Dict, List, Any, Tuple, Optional
from itertools import product
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

# 导入简化策略系统
from scripts.simple_working_strategy import SimpleMeanReversionStrategy, SimpleStrategyBacktester

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedMeanReversionStrategy(SignalGenerator):
    """优化版均值回归策略 - 支持参数配置"""

    def __init__(self,
                 lookback_period: int = 10,
                 buy_threshold: float = -0.05,
                 sell_threshold: float = 0.03,
                 max_hold_days: int = 15,
                 position_size: int = 1000,
                 min_price: float = 5.0,          # 最低价格过滤
                 max_price: float = 500.0,        # 最高价格过滤
                 volume_filter: bool = True,     # 是否启用成交量过滤
                 stop_loss: float = -0.15,        # 止损阈值
                 trailing_stop: bool = False,     # 是否启用移动止损
                 profit_take: float = 0.12):       # 止盈阈值
        super().__init__(f"OptMeanRev_L{lookback_period}_B{buy_threshold}_S{sell_threshold}_D{max_hold_days}_PS{position_size}")

        self.lookback_period = lookback_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.max_hold_days = max_hold_days
        self.position_size = position_size
        self.min_price = min_price
        self.max_price = max_price
        self.volume_filter = volume_filter
        self.stop_loss = stop_loss
        self.trailing_stop = trailing_stop
        self.profit_take = profit_take

        # 持仓管理
        self.positions = {}
        self.trade_count = 0
        self.successful_trades = 0

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
        """更新持仓信息"""
        for stock_code in list(self.positions.keys()):
            position = self.positions[stock_code]
            entry_date = pd.to_datetime(position['entry_date'])
            current_date = pd.to_datetime(snapshot.date)
            position['hold_days'] = (current_date - entry_date).days

            # 更新最高价（用于移动止损）
            if stock_code in snapshot.stock_data:
                current_price = snapshot.stock_data[stock_code]['close']
                position['max_price'] = max(position.get('max_price', current_price), current_price)

    def _check_sell_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """检查卖出信号"""
        instructions = []

        for stock_code, position in list(self.positions.items()):
            sell_reasons = []

            if stock_code in snapshot.stock_data:
                current_price = snapshot.stock_data[stock_code]['close']
                entry_price = position['entry_price']
                price_change = (current_price - entry_price) / entry_price
                max_price = position.get('max_price', entry_price)

                # 1. 盈利目标达到
                if price_change >= self.profit_take:
                    sell_reasons.append(f"Profit target: {price_change:.4f} >= {self.profit_take}")

                # 2. 止损保护
                if price_change <= self.stop_loss:
                    sell_reasons.append(f"Stop loss: {price_change:.4f} <= {self.stop_loss}")

                # 3. 移动止损
                if self.trailing_stop and max_price > entry_price:
                    trailing_loss = (current_price - max_price) / max_price
                    if trailing_loss <= -0.05:  # 移动止损5%
                        sell_reasons.append(f"Trailing stop: {trailing_loss:.4f} <= -0.05")

                # 4. 均值回归卖出
                if price_change >= self.sell_threshold:
                    sell_reasons.append(f"Mean reversion: {price_change:.4f} >= {self.sell_threshold}")

                # 5. 时间止损
                if position.get('hold_days', 0) >= self.max_hold_days:
                    sell_reasons.append(f"Time exit: {position['hold_days']} >= {self.max_hold_days}")

            # 执行卖出
            if sell_reasons:
                instructions.append(TradingInstruction(
                    stock_code=stock_code,
                    action='SELL',
                    quantity=position['quantity'],
                    reason=f"Sell - {'; '.join(sell_reasons)}",
                    timestamp=snapshot.date
                ))

                # 计算交易收益
                if stock_code in snapshot.stock_data:
                    current_price = snapshot.stock_data[stock_code]['close']
                    entry_price = position['entry_price']
                    pnl = (current_price - entry_price) * position['quantity']
                    if pnl > 0:
                        self.successful_trades += 1

                self.trade_count += 1
                logger.info(f"卖出: {stock_code}, 原因: {'; '.join(sell_reasons)}")

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

                # 基本买入条件
                if reversion_score <= self.buy_threshold:
                    if stock_code in snapshot.stock_data:
                        current_price = snapshot.stock_data[stock_code]['close']

                        # 价格过滤
                        if current_price < self.min_price or current_price > self.max_price:
                            continue

                        # 成交量过滤
                        if self.volume_filter and 'volume' in snapshot.stock_data[stock_code]:
                            avg_volume = snapshot.stock_data[stock_code].get('volume', 0)
                            if avg_volume < 1000000:  # 成交量过滤
                                continue

                        # 资金控制：限制同时持仓数量
                        if len(self.positions) >= 3:  # 最多同时持有3只股票
                            continue

                        instructions.append(TradingInstruction(
                            stock_code=stock_code,
                            action='BUY',
                            quantity=self.position_size,
                            reason=f"Buy signal: mean reversion {reversion_score:.4f} <= {self.buy_threshold}",
                            timestamp=snapshot.date
                        ))

                        logger.info(f"买入: {stock_code}, 均值回归: {reversion_score:.4f}, 价格: {current_price:.2f}")

        return instructions

    def on_trade_executed(self, instruction: TradingInstruction, execution_price: float, execution_time: str):
        """交易执行回调"""
        if instruction.action == 'BUY':
            self.positions[instruction.stock_code] = {
                'entry_price': execution_price,
                'entry_date': execution_time,
                'quantity': instruction.quantity,
                'hold_days': 0,
                'max_price': execution_price
            }

        elif instruction.action == 'SELL':
            if instruction.stock_code in self.positions:
                position = self.positions.pop(instruction.stock_code)
                # 收益计算在卖出信号检查中已经完成

    def get_strategy_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        win_rate = self.successful_trades / max(self.trade_count, 1) * 100

        return {
            "current_positions": len(self.positions),
            "total_trades": self.trade_count,
            "successful_trades": self.successful_trades,
            "win_rate": win_rate,
            "positions": list(self.positions.keys())
        }

class ParameterOptimizationEngine:
    """参数优化引擎"""

    def __init__(self, data_dir: str = "data/historical/stocks/complete_csi800/stocks"):
        self.data_dir = Path(data_dir)
        self.results_dir = Path("parameter_optimization_results")
        self.results_dir.mkdir(exist_ok=True)

    def optimize_strategy(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """运行参数优化"""
        logger.info("🚀 启动参数优化引擎")
        logger.info(f"股票池: {stock_codes}")
        logger.info(f"测试期间: {start_date} 到 {end_date}")

        # 定义参数网格
        parameter_grid = self._create_parameter_grid()

        logger.info(f"参数组合数量: {len(parameter_grid)}")

        results = []
        total_combinations = len(parameter_grid)

        for i, params in enumerate(parameter_grid, 1):
            logger.info(f"\n--- 测试参数组合 {i}/{total_combinations} ---")
            logger.info(f"参数: {params}")

            try:
                # 创建策略实例
                strategy = OptimizedMeanReversionStrategy(**params)

                # 运行回测
                backtester = OptimizedBacktester(self.data_dir)
                result = backtester.run_strategy_test(strategy, stock_codes, start_date, end_date)

                # 添加参数信息
                result['parameters'] = params
                result['strategy_name'] = strategy.name

                # 添加策略统计
                if hasattr(strategy, 'get_strategy_stats'):
                    result['strategy_stats'] = strategy.get_strategy_stats()

                # 计算综合评分
                result['optimization_score'] = self._calculate_optimization_score(result)

                results.append(result)

                # 输出简要结果
                total_return = result.get('total_return', 0)
                sharpe_ratio = result.get('sharpe_ratio', 0)
                max_dd = result.get('max_drawdown', 0)
                trades = len(result.get('trades', []))
                score = result['optimization_score']

                logger.info(f"  总收益: {total_return:.2f}%")
                logger.info(f"  夏普比率: {sharpe_ratio:.2f}")
                logger.info(f"  最大回撤: {max_dd:.2f}%")
                logger.info(f"  交易次数: {trades}")
                logger.info(f"  优化评分: {score:.2f}")

                # 保存单个结果
                self._save_single_result(result, i)

            except Exception as e:
                logger.error(f"参数组合 {i} 测试失败: {e}")
                results.append({
                    'parameters': params,
                    'error': str(e),
                    'optimization_score': -999
                })

        # 分析和排序结果
        results.sort(key=lambda x: x['optimization_score'], reverse=True)

        # 生成综合报告
        self._generate_optimization_report(results)

        return results

    def _create_parameter_grid(self) -> List[Dict[str, Any]]:
        """创建参数网格"""
        # 参数范围
        lookback_periods = [5, 8, 10, 12, 15]
        buy_thresholds = [-0.03, -0.05, -0.08, -0.10, -0.12]
        sell_thresholds = [0.02, 0.03, 0.05, 0.06, 0.08]
        max_hold_days = [10, 15, 20, 25, 30]
        position_sizes = [500, 1000, 1500]

        # 生成所有组合
        combinations = list(product(
            lookback_periods,
            buy_thresholds,
            sell_thresholds,
            max_hold_days,
            position_sizes
        ))

        # 转换为参数字典
        parameter_grid = []
        for combo in combinations:
            param_dict = {
                'lookback_period': combo[0],
                'buy_threshold': combo[1],
                'sell_threshold': combo[2],
                'max_hold_days': combo[3],
                'position_size': combo[4],
                'min_price': 3.0,
                'max_price': 300.0,
                'volume_filter': True,
                'stop_loss': -0.20,
                'trailing_stop': False,
                'profit_take': 0.15
            }
            parameter_grid.append(param_dict)

        return parameter_grid

    def _calculate_optimization_score(self, result: Dict[str, Any]) -> float:
        """计算优化评分"""
        if 'error' in result:
            return -999

        total_return = result.get('total_return', 0)
        sharpe_ratio = result.get('sharpe_ratio', 0)
        max_drawdown = result.get('max_drawdown', 100)
        trade_count = len(result.get('trades', []))

        # 策略统计
        strategy_stats = result.get('strategy_stats', {})
        win_rate = strategy_stats.get('win_rate', 0)

        # 综合评分（权重可调）
        score = 0

        # 收益权重 40%
        if total_return > 0:
            score += min(total_return * 0.4, 40)  # 最高40分

        # 夏普比率权重 25%
        if sharpe_ratio > 0:
            score += min(sharpe_ratio * 12.5, 25)  # 最高25分

        # 回撤控制权重 20%
        if max_drawdown < 20:
            score += max(0, 20 - max_drawdown)  # 回撤越小分数越高

        # 交易频率权重 10%
        if 5 <= trade_count <= 50:
            score += 10
        elif trade_count > 50:
            score += max(0, 10 - (trade_count - 50) * 0.2)

        # 胜率权重 5%
        if win_rate > 50:
            score += min(win_rate * 0.1, 5)

        return score

    def _save_single_result(self, result: Dict[str, Any], index: int):
        """保存单个参数测试结果"""
        result_file = self.results_dir / f"optimization_result_{index:03d}.json"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    def _generate_optimization_report(self, results: List[Dict[str, Any]]):
        """生成优化报告"""
        report_lines = []
        report_lines.append("# Parameter Optimization Report - 参数优化报告")
        report_lines.append("=" * 80)
        report_lines.append(f"**优化时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**测试参数组合**: {len(results)}")
        report_lines.append("")

        # 成功测试统计
        successful_tests = len([r for r in results if 'error' not in r])
        profitable_strategies = len([r for r in results if 'error' not in r and r.get('total_return', 0) > 0])

        report_lines.append("## 📊 优化统计")
        report_lines.append("")
        report_lines.append(f"- **成功测试**: {successful_tests}/{len(results)} ({successful_tests/len(results)*100:.1f}%)")
        report_lines.append(f"- **盈利策略**: {profitable_strategies}/{successful_tests} ({profitable_strategies/max(successful_tests, 1)*100:.1f}%)")
        report_lines.append("")

        # Top 10 策略
        report_lines.append("## 🏆 Top 10 策略组合")
        report_lines.append("")
        report_lines.append("| 排名 | 优化评分 | 总收益 | 夏普比率 | 最大回撤 | 交易次数 | 胜率 | 参数配置 |")
        report_lines.append("|------|----------|--------|----------|----------|----------|------|----------|")

        top_results = results[:10]
        for i, result in enumerate(top_results, 1):
            if 'error' in result:
                continue

            score = result['optimization_score']
            total_return = result.get('total_return', 0)
            sharpe = result.get('sharpe_ratio', 0)
            max_dd = result.get('max_drawdown', 0)
            trades = len(result.get('trades', []))

            strategy_stats = result.get('strategy_stats', {})
            win_rate = strategy_stats.get('win_rate', 0)

            params = result['parameters']
            param_str = f"L{params['lookback_period']}_B{params['buy_threshold']}_S{params['sell_threshold']}_D{params['max_hold_days']}"

            status = "✅" if total_return > 0 else "❌"
            report_lines.append(f"| {i} | {score:.1f} | {total_return:.2f}% | {sharpe:.2f} | "
                              f"{max_dd:.2f}% | {trades} | {win_rate:.1f}% | {status} {param_str} |")

        # 最佳策略详情
        if top_results and 'error' not in top_results[0]:
            best = top_results[0]
            report_lines.append("")
            report_lines.append("## 🎯 最佳策略详情")
            report_lines.append("")

            params = best['parameters']
            report_lines.append(f"**策略名称**: {best['strategy_name']}")
            report_lines.append(f"**优化评分**: {best['optimization_score']:.2f}")
            report_lines.append(f"**总收益**: {best.get('total_return', 0):.2f}%")
            report_lines.append(f"**夏普比率**: {best.get('sharpe_ratio', 0):.2f}")
            report_lines.append(f"**最大回撤**: {best.get('max_drawdown', 0):.2f}%")
            report_lines.append(f"**交易次数**: {len(best.get('trades', []))}")

            strategy_stats = best.get('strategy_stats', {})
            report_lines.append(f"**胜率**: {strategy_stats.get('win_rate', 0):.1f}%")
            report_lines.append("")

            report_lines.append("### 参数配置")
            report_lines.append(f"- 回看周期: {params['lookback_period']} 天")
            report_lines.append(f"- 买入阈值: {params['buy_threshold']}")
            report_lines.append(f"- 卖出阈值: {params['sell_threshold']}")
            report_lines.append(f"- 最大持有: {params['max_hold_days']} 天")
            report_lines.append(f"- 仓位大小: {params['position_size']}")
            report_lines.append(f"- 价格过滤: {params['min_price']} - {params['max_price']}")
            report_lines.append(f"- 止损设置: {params['stop_loss']}")
            report_lines.append(f"- 止盈设置: {params['profit_take']}")

        # 参数敏感性分析
        report_lines.append("")
        report_lines.append("## 📈 参数敏感性分析")
        report_lines.append("")

        # 分析各参数的影响
        parameter_analysis = self._analyze_parameter_sensitivity(results)
        for param, analysis in parameter_analysis.items():
            report_lines.append(f"### {param}")
            report_lines.append(f"- 最佳值: {analysis['best_value']}")
            report_lines.append(f"- 平均收益: {analysis['avg_return']:.2f}%")
            report_lines.append(f"- 收益标准差: {analysis['std_return']:.2f}%")
            report_lines.append("")

        # 优化建议
        report_lines.append("## 💡 优化建议")
        report_lines.append("")

        if profitable_strategies > 0:
            report_lines.append("### ✅ 成功策略特征")
            report_lines.append("1. **参数平衡**: 买入/卖出阈值设置合理")
            report_lines.append("2. **时间控制**: 适中的最大持有天数")
            report_lines.append("3. **风险控制**: 有效的止损机制")
            report_lines.append("4. **仓位管理**: 合理的仓位大小")
        else:
            report_lines.append("### ⚠️ 改进方向")
            report_lines.append("1. **放宽买入条件**: 降低买入阈值")
            report_lines.append("2. **调整卖出时机**: 优化卖出阈值")
            report_lines.append("3. **延长持有时间**: 增加最大持有天数")
            report_lines.append("4. **降低交易成本**: 减少交易频率")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        # 保存报告
        report_file = self.results_dir / "parameter_optimization_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"优化报告已保存到: {report_file}")

        return profitable_strategies

    def _analyze_parameter_sensitivity(self, results: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """分析参数敏感性"""
        parameter_analysis = {}

        # 参数列表
        parameters = ['lookback_period', 'buy_threshold', 'sell_threshold', 'max_hold_days', 'position_size']

        for param in parameters:
            returns_by_param = {}

            for result in results:
                if 'error' in result:
                    continue

                param_value = result['parameters'][param]
                total_return = result.get('total_return', 0)

                if param_value not in returns_by_param:
                    returns_by_param[param_value] = []
                returns_by_param[param_value].append(total_return)

            # 计算统计信息
            best_value = None
            best_avg_return = float('-inf')

            for value, returns in returns_by_param.items():
                avg_return = np.mean(returns)
                std_return = np.std(returns)

                if avg_return > best_avg_return:
                    best_avg_return = avg_return
                    best_value = value

                parameter_analysis[param] = {
                    'best_value': best_value,
                    'avg_return': avg_return,
                    'std_return': std_return
                }

        return parameter_analysis

class OptimizedBacktester:
    """优化回测器"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def run_strategy_test(self, strategy: SignalGenerator, stock_codes: List[str],
                          start_date: str, end_date: str) -> Dict[str, Any]:
        """运行策略测试"""
        class OptimizedBacktestEngine(BiasFreeBacktestEngine):
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

        backtest_engine = OptimizedBacktestEngine(self, strategy)
        backtest_engine.add_signal_generator(strategy)

        return backtest_engine.run_bias_free_backtest(stock_codes, start_date, end_date)

    def enhance_with_factors(self, snapshot: DataSnapshot) -> DataSnapshot:
        """添加因子数据"""
        enhanced_factor_data = {}

        for stock_code, stock_data in snapshot.stock_data.items():
            enhanced_factor_data[stock_code] = {}

            # 获取历史数据
            data = self._load_stock_historical_data(stock_code, snapshot.date)
            if data is None or len(data) < 30:
                continue

            # 计算均值回归因子
            reversion_score = self._calculate_mean_reversion(data, 10)
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

    def _calculate_mean_reversion(self, data: pd.DataFrame, lookback_period: int = 10) -> float:
        """计算均值回归因子"""
        if len(data) < lookback_period + 1:
            return np.nan

        recent_prices = data['close'].iloc[-lookback_period:]
        current_price = data['close'].iloc[-1]
        mean_price = recent_prices.mean()

        if mean_price > 0:
            deviation = (current_price - mean_price) / mean_price
            return deviation

        return np.nan

def main():
    """主函数"""
    logger.info("🚀 启动参数优化引擎")
    logger.info("=" * 60)

    # 创建优化引擎
    optimizer = ParameterOptimizationEngine()

    # 测试参数
    stock_codes = ['000001', '000002', '600036', '600519', '000858']
    start_date = '2022-01-01'
    end_date = '2023-12-31'

    # 运行优化
    results = optimizer.optimize_strategy(stock_codes, start_date, end_date)

    # 统计结果
    successful_tests = len([r for r in results if 'error' not in r])
    profitable_strategies = len([r for r in results if 'error' not in r and r.get('total_return', 0) > 0])

    logger.info("\n" + "=" * 60)
    logger.info("📊 优化总结")
    logger.info(f"成功测试: {successful_tests}")
    logger.info(f"盈利策略: {profitable_strategies}")

    if profitable_strategies > 0:
        best_result = results[0]  # 已按评分排序
        logger.info("🎉 成功找到有效策略组合！")
        logger.info(f"最佳策略: {best_result['strategy_name']}")
        logger.info(f"优化评分: {best_result['optimization_score']:.2f}")
        logger.info(f"总收益: {best_result.get('total_return', 0):.2f}%")
        logger.info("查看详细报告了解所有策略组合。")
    else:
        logger.info("⚠️ 未找到盈利策略，建议进一步调整参数范围。")

    logger.info("=" * 60)

if __name__ == "__main__":
    main()