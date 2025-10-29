#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
无偏差回测引擎 (Bias-Free Backtesting Engine)
严格时间序列隔离，从根本上杜绝前视偏差
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging
from pathlib import Path
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TradingInstruction:
    """交易指令数据类"""
    stock_code: str
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: Optional[float] = None  # None表示市价单
    timestamp: datetime = None
    reason: str = ""  # 交易理由

@dataclass
class DataSnapshot:
    """数据快照 - T-1日收盘时的完整数据状态"""
    date: datetime
    stock_data: Dict[str, pd.DataFrame]  # 每只股票的完整历史数据
    market_data: pd.DataFrame  # 市场整体数据
    factor_data: Dict[str, pd.Series]  # 计算好的因子数据
    is_valid: bool = True

class SignalGenerator(ABC):
    """信号生成器抽象基类 - 只能访问T-1日及之前的数据"""

    def __init__(self, name: str):
        self.name = name
        self.last_snapshot_date = None

    @abstractmethod
    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        """
        生成交易信号
        只能使用snapshot中的T-1日及之前的数据
        """
        pass

    def validate_data_access(self, snapshot: DataSnapshot, current_date: datetime) -> bool:
        """验证数据访问是否合规（没有使用未来数据）"""
        if snapshot.date >= current_date:
            logger.error(f"数据访问违规: 快照日期 {snapshot.date} >= 当前日期 {current_date}")
            return False
        return True

class ExecutionEngine:
    """交易执行引擎 - 只执行指令，不生成信号"""

    def __init__(self, commission_rate: float = 0.0003, stamp_duty_rate: float = 0.001):
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.slippage_rate = 0.001  # 千分之一滑点

    def execute_instructions(self,
                           instructions: List[TradingInstruction],
                           market_data: pd.DataFrame,
                           execution_date: datetime) -> Dict[str, Any]:
        """
        执行交易指令
        只使用当日的市场数据执行交易
        """
        execution_results = []
        total_cost = 0

        for instruction in instructions:
            result = self._execute_single_instruction(instruction, market_data, execution_date)
            execution_results.append(result)
            total_cost += result.get('transaction_cost', 0)

        return {
            'executed_trades': execution_results,
            'total_cost': total_cost,
            'execution_date': execution_date,
            'instructions_count': len(instructions)
        }

    def _execute_single_instruction(self,
                                 instruction: TradingInstruction,
                                 market_data: pd.DataFrame,
                                 execution_date: datetime) -> Dict[str, Any]:
        """执行单个交易指令"""
        stock_code = instruction.stock_code

        # 获取当日价格数据
        stock_price_data = market_data[market_data['stock_code'] == stock_code]
        if stock_price_data.empty:
            return {
                'instruction': instruction,
                'status': 'FAILED',
                'reason': 'No price data available'
            }

        # 模拟执行价格（考虑滑点）
        reference_price = stock_price_data['open'].iloc[0]

        if instruction.action == 'BUY':
            execution_price = reference_price * (1 + self.slippage_rate)
        else:  # SELL
            execution_price = reference_price * (1 - self.slippage_rate)

        # 计算交易成本
        trade_value = execution_price * instruction.quantity
        commission = trade_value * self.commission_rate

        if instruction.action == 'SELL':
            stamp_duty = trade_value * self.stamp_duty_rate
        else:
            stamp_duty = 0

        total_cost = commission + stamp_duty

        return {
            'instruction': instruction,
            'status': 'EXECUTED',
            'execution_price': execution_price,
            'quantity': instruction.quantity,
            'trade_value': trade_value,
            'commission': commission,
            'stamp_duty': stamp_duty,
            'transaction_cost': total_cost,
            'execution_time': execution_date
        }

class BiasFreeBacktestEngine:
    """无偏差回测引擎主类"""

    def __init__(self):
        self.signal_generators: List[SignalGenerator] = []
        self.execution_engine = ExecutionEngine()
        self.data_manager = None
        self.audit_trail: List[Dict] = []

        # 回测配置
        self.config = {
            'start_date': '2020-01-01',
            'end_date': '2024-12-31',
            'initial_capital': 1000000,
            'rebalance_frequency': 'weekly',  # 周频调仓
        }

    def add_signal_generator(self, generator: SignalGenerator):
        """添加信号生成器"""
        self.signal_generators.append(generator)
        logger.info(f"添加信号生成器: {generator.name}")

    def load_stock_data(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """加载股票数据"""
        stock_data = {}

        for stock_code in stock_codes:
            # 尝试从多个数据源加载
            data = self._load_single_stock_data(stock_code, start_date, end_date)
            if not data.empty:
                stock_data[stock_code] = data

        logger.info(f"成功加载 {len(stock_data)} 只股票数据")
        return stock_data

    def _load_single_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载单只股票数据"""
        data_sources = [
            Path(f'data/historical/stocks/complete_csi800/stocks'),
            Path(f'data/historical/stocks/csi300_5year/stocks')
        ]

        all_data = []

        for data_source in data_sources:
            if not data_source.exists():
                continue

            for year_dir in data_source.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue

                file_path = year_dir / f"{stock_code}.csv"
                if file_path.exists():
                    try:
                        df = pd.read_csv(file_path)
                        df['date'] = pd.to_datetime(df['date'])
                        df['stock_code'] = stock_code

                        # 日期过滤
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        if not df.empty:
                            all_data.append(df)
                    except Exception as e:
                        logger.warning(f"加载 {file_path} 失败: {e}")

        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data = combined_data.drop_duplicates(subset=['date']).sort_values('date')
            return combined_data

        return pd.DataFrame()

    def create_data_snapshot(self,
                           date: datetime,
                           stock_data: Dict[str, pd.DataFrame]) -> DataSnapshot:
        """
        创建数据快照
        严格确保只包含date及之前的数据
        """
        snapshot_data = {}
        factor_data = {}

        for stock_code, data in stock_data.items():
            # 只取date及之前的数据
            historical_data = data[data['date'] <= date].copy()
            if not historical_data.empty:
                snapshot_data[stock_code] = historical_data

                # 预计算基础因子（使用历史数据）
                factor_data[stock_code] = self._calculate_basic_factors(historical_data)

        # 创建市场数据快照
        market_snapshot = self._create_market_snapshot(snapshot_data, date)

        return DataSnapshot(
            date=date,
            stock_data=snapshot_data,
            market_data=market_snapshot,
            factor_data=factor_data,
            is_valid=len(snapshot_data) > 0
        )

    def _calculate_basic_factors(self, data: pd.DataFrame) -> pd.Series:
        """计算基础因子（只使用历史数据）"""
        factors = pd.Series()

        if len(data) < 20:
            return factors

        # 成交量激增因子
        if len(data) >= 20:
            data['volume_ma20'] = data['volume'].rolling(20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_ma20']
            factors['volume_surge'] = data['volume_ratio'].iloc[-1]

        # 动量强度因子 (LWR)
        if len(data) >= 14:
            high_14 = data['high'].rolling(14).max()
            low_14 = data['low'].rolling(14).min()
            close_curr = data['close']

            # LWR = (收盘价 - 14日最低价) / (14日最高价 - 14日最低价) * (-100)
            lwr = -100 * (close_curr - low_14) / (high_14 - low_14)
            factors['momentum_strength'] = lwr.iloc[-1]

        # 移动平均排列
        if len(data) >= 20:
            data['ma20'] = data['close'].rolling(20).mean()
            factors['ma_arrangement'] = (data['close'].iloc[-1] - data['ma20'].iloc[-1]) / data['ma20'].iloc[-1]

        return factors

    def _create_market_snapshot(self, stock_data: Dict[str, pd.DataFrame], date: datetime) -> pd.DataFrame:
        """创建市场数据快照"""
        market_rows = []

        for stock_code, data in stock_data.items():
            if not data.empty:
                # 获取最新的数据行（不超过指定日期）
                latest_data = data[data['date'] <= date].iloc[-1]
                market_rows.append({
                    'stock_code': stock_code,
                    'date': latest_data['date'],
                    'open': latest_data['open'],
                    'high': latest_data['high'],
                    'low': latest_data['low'],
                    'close': latest_data['close'],
                    'volume': latest_data['volume']
                })

        return pd.DataFrame(market_rows)

    def run_bias_free_backtest(self,
                             stock_codes: List[str],
                             start_date: str,
                             end_date: str) -> Dict[str, Any]:
        """
        运行无偏差回测
        严格遵循时间序列隔离原则
        """
        logger.info("开始无偏差回测...")

        # 加载完整数据集
        full_stock_data = self.load_stock_data(stock_codes, start_date, end_date)

        if not full_stock_data:
            raise ValueError("无法加载任何股票数据")

        # 生成交易日期列表
        trading_dates = self._generate_trading_dates(full_stock_data, start_date, end_date)

        backtest_results = {
            'trades': [],
            'portfolio_values': [],
            'daily_returns': [],
            'audit_trail': [],
            'performance_metrics': {}
        }

        cash = float(self.config['initial_capital'])
        positions: Dict[str, Dict[str, float]] = {}
        portfolio_value, position_value = self._compute_portfolio_value(
            cash, positions, full_stock_data, trading_dates[0]
        )
        backtest_results['portfolio_values'].append({
            'date': trading_dates[0],
            'portfolio_value': portfolio_value,
            'cash': cash,
            'position_value': position_value
        })

        # 主回测循环
        for i, trading_date in enumerate(trading_dates[:-1]):  # 最后一天不生成信号
            logger.info(f"处理交易日期: {trading_date.strftime('%Y-%m-%d')}")

            # 步骤1: T-1日收盘后，生成T日交易指令
            signal_date = trading_date
            execution_date = trading_dates[i + 1]

            # 创建数据快照（严格限制为T-1日及之前的数据）
            snapshot = self.create_data_snapshot(signal_date, full_stock_data)

            if not snapshot.is_valid:
                logger.warning(f"数据快照无效: {signal_date}")
                continue

            # 生成交易信号
            all_instructions = []
            for generator in self.signal_generators:
                # 验证数据访问合规性
                if not generator.validate_data_access(snapshot, execution_date):
                    logger.error(f"信号生成器 {generator.name} 数据访问违规")
                    continue

                instructions = generator.generate_signals(snapshot)
                all_instructions.extend(instructions)

                # 记录审计轨迹
                self.audit_trail.append({
                    'date': signal_date,
                    'generator': generator.name,
                    'instructions_count': len(instructions),
                    'snapshot_valid': snapshot.is_valid
                })

            # 步骤2: T日执行交易
            if all_instructions:
                market_data = self._get_market_data_for_date(full_stock_data, execution_date)
                execution_result = self.execution_engine.execute_instructions(
                    all_instructions, market_data, execution_date
                )

                backtest_results['trades'].extend(execution_result['executed_trades'])

                # 根据成交结果更新现金和持仓
                cash = self._apply_execution_results(execution_result, positions, cash)

            # 计算当日组合总价值
            portfolio_value, position_value = self._compute_portfolio_value(
                cash, positions, full_stock_data, execution_date
            )
            backtest_results['portfolio_values'].append({
                'date': execution_date,
                'portfolio_value': portfolio_value,
                'cash': cash,
                'position_value': position_value
            })

            if all_instructions:
                logger.info(
                    "执行 %d 个指令，组合价值: %.2f (现金 %.2f, 持仓 %.2f)",
                    len(all_instructions),
                    portfolio_value,
                    cash,
                    position_value
                )
            else:
                logger.debug(
                    "无交易，组合价值: %.2f (现金 %.2f, 持仓 %.2f)",
                    portfolio_value,
                    cash,
                    position_value
                )

        # 计算性能指标
        performance = self._calculate_performance_metrics(
            backtest_results['portfolio_values']
        )
        backtest_results['performance_metrics'] = performance
        backtest_results['daily_returns'] = performance.get('daily_returns', [])
        performance.pop('daily_returns', None)

        backtest_results['audit_trail'] = self.audit_trail

        logger.info("无偏差回测完成")
        return backtest_results

    def _generate_trading_dates(self,
                              stock_data: Dict[str, pd.DataFrame],
                              start_date: str,
                              end_date: str) -> List[datetime]:
        """生成交易日期列表"""
        all_dates = set()

        for data in stock_data.values():
            dates = data['date'].dt.date.unique()
            all_dates.update(dates)

        trading_dates = sorted([datetime.combine(date, datetime.min.time())
                              for date in all_dates])

        # 过滤指定日期范围
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        return [date for date in trading_dates if start_dt <= date <= end_dt]

    def _get_market_data_for_date(self,
                                stock_data: Dict[str, pd.DataFrame],
                                date: datetime) -> pd.DataFrame:
        """获取指定日期的市场数据"""
        market_rows = []

        for stock_code, data in stock_data.items():
            daily_data = data[data['date'].dt.date == date.date()]
            if not daily_data.empty:
                row = daily_data.iloc[0].copy()
                row['stock_code'] = stock_code
                market_rows.append(row)

        return pd.DataFrame(market_rows)

    def _apply_execution_results(self,
                                 execution_result: Dict[str, Any],
                                 positions: Dict[str, Dict[str, float]],
                                 cash: float) -> float:
        """根据成交结果更新现金与持仓"""
        for trade in execution_result.get('executed_trades', []):
            if trade.get('status') != 'EXECUTED':
                continue

            instruction: TradingInstruction = trade['instruction']
            stock_code = instruction.stock_code
            quantity = float(trade.get('quantity', 0))
            execution_price = float(trade.get('execution_price', 0))
            trade_value = float(trade.get('trade_value', execution_price * quantity))
            transaction_cost = float(trade.get('transaction_cost', 0))
            action = (instruction.action or '').upper()

            if action == 'BUY':
                cash -= (trade_value + transaction_cost)
                position = positions.setdefault(stock_code, {'quantity': 0.0, 'avg_cost': 0.0})
                prev_qty = position['quantity']
                new_qty = prev_qty + quantity
                if new_qty <= 0:
                    position['quantity'] = 0.0
                    position['avg_cost'] = 0.0
                else:
                    position['avg_cost'] = ((position['avg_cost'] * prev_qty) + trade_value) / new_qty
                    position['quantity'] = new_qty
                position['last_price'] = execution_price
            elif action == 'SELL':
                position = positions.setdefault(stock_code, {'quantity': 0.0, 'avg_cost': 0.0})
                prev_qty = position['quantity']
                new_qty = prev_qty - quantity
                position['quantity'] = new_qty
                position['last_price'] = execution_price
                if new_qty <= 0:
                    positions.pop(stock_code, None)
                cash += (trade_value - transaction_cost)
            else:
                logger.warning("未知交易动作 %s，已忽略。", action)

        return cash

    def _compute_portfolio_value(self,
                                 cash: float,
                                 positions: Dict[str, Dict[str, float]],
                                 stock_data: Dict[str, pd.DataFrame],
                                 valuation_date: datetime) -> Tuple[float, float]:
        """计算组合总价值与持仓市值"""
        position_value = 0.0
        for stock_code, position in positions.items():
            quantity = position.get('quantity', 0.0)
            if quantity == 0:
                continue

            data = stock_data.get(stock_code)
            price = position.get('last_price', 0.0)
            if data is not None:
                price_data = data[data['date'] <= valuation_date]
                if not price_data.empty:
                    price = float(price_data.iloc[-1]['close'])
            position['last_price'] = price
            position_value += quantity * price

        total_value = cash + position_value
        return total_value, position_value

    def _calculate_performance_metrics(self, portfolio_values: List[Dict]) -> Dict[str, float]:
        """计算性能指标"""
        if len(portfolio_values) < 2:
            return {}

        values = [pv['portfolio_value'] for pv in portfolio_values]
        initial_value = values[0]
        final_value = values[-1]

        # 计算日收益率
        daily_returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)

        # 年化收益率
        total_days = len(values)
        total_return = (final_value - initial_value) / initial_value
        annual_return = (1 + total_return) ** (252 / total_days) - 1

        # 夏普比率
        if daily_returns:
            annual_volatility = np.std(daily_returns) * np.sqrt(252)
            sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        else:
            sharpe_ratio = 0

        # 最大回撤
        peak = initial_value
        max_drawdown = 0
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': annual_volatility if daily_returns else 0,
            'total_days': total_days,
            'daily_returns': daily_returns
        }

# 示例信号生成器
class VolumeSurgeSignalGenerator(SignalGenerator):
    """成交量激增信号生成器"""

    def __init__(self):
        super().__init__("VolumeSurge")

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'volume_surge' in factors and not pd.isna(factors['volume_surge']):
                volume_ratio = factors['volume_surge']

                # 成交量激增超过2倍时买入
                if volume_ratio > 2.0:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,  # 固定数量，实际应根据资金管理
                        reason=f"Volume surge: {volume_ratio:.2f}"
                    ))

        return instructions

class MomentumSignalGenerator(SignalGenerator):
    """动量信号生成器"""

    def __init__(self):
        super().__init__("Momentum")

    def generate_signals(self, snapshot: DataSnapshot) -> List[TradingInstruction]:
        instructions = []

        for stock_code, factors in snapshot.factor_data.items():
            if 'momentum_strength' in factors and not pd.isna(factors['momentum_strength']):
                lwr = factors['momentum_strength']

                # LWR接近-30时买入（超卖反弹）
                if lwr < -30:
                    instructions.append(TradingInstruction(
                        stock_code=stock_code,
                        action='BUY',
                        quantity=1000,
                        reason=f"Momentum strength: {lwr:.2f}"
                    ))

        return instructions

def main():
    """主函数 - 测试无偏差回测引擎"""
    logger.info("=== 无偏差回测引擎测试 ===")

    # 创建回测引擎
    engine = BiasFreeBacktestEngine()

    # 添加信号生成器
    engine.add_signal_generator(VolumeSurgeSignalGenerator())
    engine.add_signal_generator(MomentumSignalGenerator())

    # 测试股票列表
    test_stocks = ['000001', '600000', '000002', '600519', '000858']

    # 运行回测
    try:
        results = engine.run_bias_free_backtest(
            stock_codes=test_stocks,
            start_date='2022-01-01',
            end_date='2022-12-31'
        )

        # 保存结果
        output_dir = Path("bias_free_backtest_results")
        output_dir.mkdir(exist_ok=True)

        results_file = output_dir / "bias_free_backtest_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        # 打印关键指标
        metrics = results['performance_metrics']
        print(f"\n=== 无偏差回测结果 ===")
        print(f"年化收益率: {metrics.get('annual_return', 0):.2%}")
        print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"总交易数: {len(results['trades'])}")
        print(f"审计轨迹记录: {len(results['audit_trail'])}")

        logger.info(f"结果已保存至: {results_file}")

    except Exception as e:
        logger.error(f"回测执行失败: {e}")
        raise

if __name__ == "__main__":
    main()
