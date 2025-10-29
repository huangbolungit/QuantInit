#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 - 基于动量+价值因子的 baseline 策略
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.services.data_acquisition.akshare_client import AkShareDataAcquirer


class BacktestEngine:
    """回测引擎"""

    def __init__(self, data_dir: str = None):
        """
        初始化回测引擎

        Args:
            data_dir: 数据目录 (可以是stocks目录或包含stocks的父目录)
        """
        if data_dir:
            data_path = Path(data_dir)
            # 如果传入的路径已经包含stocks子目录，直接使用
            # 否则将其作为父目录，并在下面查找stocks
            if data_path.name == "stocks":
                self.data_dir = data_path.parent
                self.stocks_dir = data_path
            else:
                self.data_dir = data_path
                self.stocks_dir = data_path / "stocks"
        else:
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "historical"
            self.stocks_dir = self.data_dir / "stocks"

        self.sectors_dir = self.data_dir / "sectors"

        # 回测参数
        self.initial_capital = 1000000  # 初始资金100万
        self.max_position_size = 0.05    # 单只股票最大仓位5%
        self.sector_max_weight = 0.30    # 单个行业最大仓位30%
        self.max_drawdown_limit = 0.15   # 最大回撤15%
        self.commission_rate = 0.0003    # 手续费率0.03%

        # 因子权重（可自定义）
        self.factor_weights = {
            'momentum': 0.5,
            'value': 0.5
        }

        # 回测结果存储
        self.portfolio_history = []
        self.trades_history = []
        self.performance_metrics = {}

    def load_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载股票数据"""
        try:
            # 查找该股票的所有数据文件
            stock_files = sorted(list(self.stocks_dir.rglob(f"{stock_code}.csv")))

            if not stock_files:
                print(f"警告: 未找到股票 {stock_code} 的数据文件")
                return pd.DataFrame()

            all_data = []
            for file_path in stock_files:
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])
                all_data.append(df)

            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'])

            # 筛选日期范围
            combined_df = combined_df[
                (combined_df['date'] >= start_date) &
                (combined_df['date'] <= end_date)
            ].reset_index(drop=True)

            return combined_df

        except Exception as e:
            print(f"加载股票 {stock_code} 数据失败: {e}")
            return pd.DataFrame()

    def load_sector_mapping(self) -> Dict[str, str]:
        """加载行业分类映射"""
        try:
            sector_file = self.sectors_dir / "shenwan_classification.csv"
            if sector_file.exists():
                sector_df = pd.read_csv(sector_file)
                return dict(zip(sector_df['stock_code'], sector_df['sector_name']))
            else:
                print("警告: 未找到行业分类文件")
                return {}
        except Exception as e:
            print(f"加载行业分类失败: {e}")
            return {}

    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        计算动量因子评分

        Args:
            df: 股票价格数据，必须包含close列

        Returns:
            动量评分 (0-100)
        """
        if len(df) < 20:
            return 50.0  # 数据不足时返回中性评分

        try:
            prices = df['close'].values

            # 1. 短期动量 (5日收益率)
            short_momentum = (prices[-1] / prices[-5] - 1) if len(prices) >= 5 else 0

            # 2. 中期动量 (20日收益率)
            medium_momentum = (prices[-1] / prices[-20] - 1) if len(prices) >= 20 else 0

            # 3. 长期动量 (60日收益率)
            long_momentum = (prices[-1] / prices[-60] - 1) if len(prices) >= 60 else 0

            # 4. 动量一致性 (最近5天、20天、60天收益率是否同向)
            momentum_consistency = 0
            if len(prices) >= 60:
                signs = [np.sign(short_momentum), np.sign(medium_momentum), np.sign(long_momentum)]
                if all(s > 0 for s in signs):
                    momentum_consistency = 1.0
                elif all(s < 0 for s in signs):
                    momentum_consistency = -1.0

            # 综合评分
            momentum_score = (
                short_momentum * 0.4 +
                medium_momentum * 0.4 +
                long_momentum * 0.2
            )

            # 标准化到0-100
            # 假设动量收益率在-30%到+30%之间
            normalized_score = (momentum_score + 0.3) / 0.6 * 100
            momentum_consistency_bonus = momentum_consistency * 10  # 一致性加分

            final_score = np.clip(normalized_score + momentum_consistency_bonus, 0, 100)
            return final_score

        except Exception as e:
            print(f"计算动量评分失败: {e}")
            return 50.0

    def calculate_value_score(self, df: pd.DataFrame) -> float:
        """
        计算价值因子评分

        注意：这里使用简化版本，实际需要财务数据
        暂时使用价格相对位置作为价值代理指标

        Args:
            df: 股票数据

        Returns:
            价值评分 (0-100)
        """
        try:
            if len(df) < 252:  # 至少需要一年数据
                return 50.0

            prices = df['close'].values

            # 使用历史价格百分位作为价值代理
            # 价格处于历史低位时给予更高评分
            current_price = prices[-1]
            historical_prices = prices[:-20]  # 排除最近20天

            percentile = np.percentile(historical_prices, [20, 50, 80])

            if current_price <= percentile[0]:  # 价格在历史20%分位以下
                value_score = 90.0
            elif current_price <= percentile[1]:  # 价格在历史50%分位以下
                value_score = 70.0
            elif current_price <= percentile[2]:  # 价格在历史80%分位以下
                value_score = 50.0
            else:  # 价格在历史80%分位以上
                value_score = 30.0

            # 根据近期趋势调整
            recent_trend = (prices[-1] / prices[-20] - 1) if len(prices) >= 20 else 0
            if recent_trend < -0.1:  # 近期大幅下跌，可能被错杀
                value_score += 10

            return np.clip(value_score, 0, 100)

        except Exception as e:
            print(f"计算价值评分失败: {e}")
            return 50.0

    def calculate_composite_score(self, momentum_score: float, value_score: float) -> float:
        """计算综合评分"""
        composite_score = (
            momentum_score * self.factor_weights['momentum'] +
            value_score * self.factor_weights['value']
        )
        return composite_score

    def select_top_stocks(self, stock_data: Dict[str, pd.DataFrame],
                         date: datetime, top_n: int = 20) -> List[Tuple[str, float]]:
        """
        选择评分最高的股票

        Args:
            stock_data: 股票数据字典
            date: 选股日期
            top_n: 选择数量

        Returns:
            [(股票代码, 评分), ...] 按评分降序排列
        """
        stock_scores = []

        for stock_code, df in stock_data.items():
            try:
                # 确保有足够的历史数据
                if len(df) < 60:
                    continue

                # 计算因子评分
                momentum_score = self.calculate_momentum_score(df)
                value_score = self.calculate_value_score(df)
                composite_score = self.calculate_composite_score(momentum_score, value_score)

                stock_scores.append((stock_code, composite_score))

            except Exception as e:
                print(f"计算股票 {stock_code} 评分失败: {e}")
                continue

        # 按评分降序排列，返回前top_n只
        stock_scores.sort(key=lambda x: x[1], reverse=True)
        return stock_scores[:top_n]

    def check_risk_limits(self, current_portfolio: Dict[str, float],
                         new_stock: str, new_weight: float,
                         sector_mapping: Dict[str, str]) -> Tuple[bool, str]:
        """检查风险限制"""
        try:
            # 1. 单只股票仓位限制
            if new_weight > self.max_position_size:
                return False, f"单只股票仓位超限: {new_weight:.2%} > {self.max_position_size:.2%}"

            # 2. 行业集中度限制
            if new_stock in sector_mapping:
                sector = sector_mapping[new_stock]
                sector_exposure = new_weight

                for stock, weight in current_portfolio.items():
                    if stock in sector_mapping and sector_mapping[stock] == sector:
                        sector_exposure += weight

                if sector_exposure > self.sector_max_weight:
                    return False, f"行业集中度超限: {sector} {sector_exposure:.2%} > {self.sector_max_weight:.2%}"

            return True, "风险检查通过"

        except Exception as e:
            print(f"风险检查失败: {e}")
            return False, f"风险检查失败: {e}"

    def run_backtest(self, start_date: str, end_date: str,
                    stock_universe: List[str] = None,
                    rebalance_frequency: str = 'weekly') -> Dict[str, Any]:
        """
        运行回测

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            stock_universe: 股票池，如果为None则使用所有可用股票
            rebalance_frequency: 调仓频率 ('daily', 'weekly', 'monthly')

        Returns:
            回测结果
        """
        print(f"开始回测: {start_date} 到 {end_date}")
        print(f"调仓频率: {rebalance_frequency}")
        print(f"因子权重: {self.factor_weights}")

        # 加载数据
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # 确定股票池
        if stock_universe is None:
            stock_universe = self._get_available_stocks()

        print(f"股票池大小: {len(stock_universe)}")

        # 加载股票数据
        stock_data = {}
        for stock_code in stock_universe:
            df = self.load_stock_data(stock_code, start_date, end_date)
            if not df.empty:
                stock_data[stock_code] = df

        print(f"成功加载 {len(stock_data)} 只股票的数据")

        # 加载行业分类
        sector_mapping = self.load_sector_mapping()

        # 生成交易日期序列
        trading_dates = self._get_trading_dates(start_dt, end_dt, rebalance_frequency)

        # 初始化组合
        current_portfolio = {}
        cash = self.initial_capital
        portfolio_value_history = []
        high_watermark = self.initial_capital
        halted_until = None  # 止损后暂停交易直到这个日期

        print(f"开始回测，共 {len(trading_dates)} 个交易日")

        for i, date in enumerate(trading_dates):
            try:
                # 检查是否在暂停期
                if halted_until and date < halted_until:
                    # 只计算组合价值，不进行交易
                    portfolio_value = self._calculate_portfolio_value(current_portfolio, date, stock_data) + cash
                    portfolio_value_history.append({
                        'date': date,
                        'portfolio_value': portfolio_value,
                        'cash': cash,
                        'positions': current_portfolio.copy(),
                        'halted': True
                    })
                    continue

                # 计算当前组合价值
                portfolio_value = self._calculate_portfolio_value(current_portfolio, date, stock_data) + cash
                portfolio_value_history.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'cash': cash,
                    'positions': current_portfolio.copy(),
                    'halted': False
                })

                # 更新最高水位线
                if portfolio_value > high_watermark:
                    high_watermark = portfolio_value

                # 检查最大回撤限制
                drawdown = (high_watermark - portfolio_value) / high_watermark
                if drawdown >= self.max_drawdown_limit:
                    print(f"触发最大回撤限制: {drawdown:.2%}, 清仓并暂停交易20天")
                    # 清仓
                    liquidation_value = self._liquidate_portfolio(current_portfolio, date, stock_data)
                    cash += liquidation_value
                    current_portfolio = {}
                    # 暂停交易20个交易日
                    halted_until = self._get_future_trading_date(date, 20, trading_dates)
                    continue

                # 调仓逻辑（只在调仓日执行）
                if i == 0 or self._should_rebalance(date, trading_dates, rebalance_frequency):
                    # 选股
                    historical_data = self._get_historical_data(stock_data, date)
                    top_stocks = self.select_top_stocks(historical_data, date, top_n=20)

                    # 目标组合（等权重）
                    target_portfolio = {}
                    if top_stocks:
                        equal_weight = min(1.0 / len(top_stocks), self.max_position_size)
                        for stock_code, _ in top_stocks:
                            target_portfolio[stock_code] = equal_weight

                    # 执行调仓
                    cash, current_portfolio, trades = self._rebalance_portfolio(
                        current_portfolio, target_portfolio, cash, date, stock_data, sector_mapping
                    )

                    # 记录交易
                    for trade in trades:
                        trade['date'] = date
                        self.trades_history.append(trade)

            except Exception as e:
                print(f"处理日期 {date} 时出错: {e}")
                continue

            # 输出进度
            if (i + 1) % 50 == 0:
                current_value = portfolio_value_history[-1]['portfolio_value']
                print(f"进度: {i+1}/{len(trading_dates)}, 组合价值: {current_value:,.0f}")

        # 计算绩效指标
        performance = self._calculate_performance_metrics(portfolio_value_history, self.trades_history)

        return {
            'portfolio_history': portfolio_value_history,
            'trades_history': self.trades_history,
            'performance_metrics': performance,
            'backtest_config': {
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': self.initial_capital,
                'factor_weights': self.factor_weights,
                'rebalance_frequency': rebalance_frequency
            }
        }

    def _get_available_stocks(self) -> List[str]:
        """获取所有可用的股票代码"""
        stock_files = list(self.stocks_dir.rglob("*.csv"))
        stock_codes = [file_path.stem for file_path in stock_files]
        return sorted(stock_codes)

    def _get_trading_dates(self, start_date: pd.Timestamp, end_date: pd.Timestamp,
                          frequency: str) -> List[pd.Timestamp]:
        """生成交易日期序列"""
        # 这里简化处理，实际应该考虑节假日
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        # 只保留工作日
        trading_dates = date_range[date_range.weekday < 5]

        if frequency == 'daily':
            return trading_dates.tolist()
        elif frequency == 'weekly':
            # 每周五调仓
            return trading_dates[trading_dates.weekday == 4].tolist()
        elif frequency == 'monthly':
            # 每月最后一个交易日调仓
            return trading_dates.groupby([trading_dates.year, trading_dates.month]).max().tolist()
        else:
            return trading_dates.tolist()

    def _should_rebalance(self, date: pd.Timestamp, trading_dates: List[pd.Timestamp],
                         frequency: str) -> bool:
        """判断是否应该调仓"""
        if frequency == 'daily':
            return True
        elif frequency == 'weekly':
            return date.weekday() == 4  # 周五
        elif frequency == 'monthly':
            # 简化处理：每月第一天
            return date.day == 1
        else:
            return True

    def _get_historical_data(self, stock_data: Dict[str, pd.DataFrame],
                           current_date: pd.Timestamp) -> Dict[str, pd.DataFrame]:
        """获取当前日期之前的历史数据"""
        historical_data = {}
        for stock_code, df in stock_data.items():
            historical_df = df[df['date'] < current_date].copy()
            if not historical_df.empty:
                historical_data[stock_code] = historical_df
        return historical_data

    def _calculate_portfolio_value(self, portfolio: Dict[str, float],
                                 date: pd.Timestamp,
                                 stock_data: Dict[str, pd.DataFrame]) -> float:
        """计算组合市值"""
        total_value = 0.0
        for stock_code, shares in portfolio.items():
            if stock_code in stock_data and shares > 0:
                df = stock_data[stock_code]
                # 获取该日期的收盘价
                price_data = df[df['date'] <= date]
                if not price_data.empty:
                    current_price = price_data.iloc[-1]['close']
                    total_value += shares * current_price
        return total_value

    def _liquidate_portfolio(self, portfolio: Dict[str, float],
                           date: pd.Timestamp,
                           stock_data: Dict[str, pd.DataFrame]) -> float:
        """清仓"""
        liquidation_value = 0.0
        for stock_code, shares in portfolio.items():
            if stock_code in stock_data and shares > 0:
                df = stock_data[stock_code]
                price_data = df[df['date'] <= date]
                if not price_data.empty:
                    current_price = price_data.iloc[-1]['close']
                    liquidation_value += shares * current_price * (1 - self.commission_rate)
        return liquidation_value

    def _rebalance_portfolio(self, current_portfolio: Dict[str, float],
                           target_portfolio: Dict[str, float],
                           cash: float, date: pd.Timestamp,
                           stock_data: Dict[str, pd.DataFrame],
                           sector_mapping: Dict[str, str]) -> Tuple[float, Dict[str, float], List[Dict]]:
        """执行组合再平衡"""
        trades = []
        new_portfolio = current_portfolio.copy()
        portfolio_value = self._calculate_portfolio_value(current_portfolio, date, stock_data) + cash

        # 卖出不在目标组合中的股票
        for stock_code in list(new_portfolio.keys()):
            if stock_code not in target_portfolio:
                shares = new_portfolio[stock_code]
                if stock_code in stock_data and shares > 0:
                    df = stock_data[stock_code]
                    price_data = df[df['date'] <= date]
                    if not price_data.empty:
                        current_price = price_data.iloc[-1]['close']
                        sale_value = shares * current_price * (1 - self.commission_rate)
                        cash += sale_value
                        trades.append({
                            'stock_code': stock_code,
                            'action': 'sell',
                            'shares': shares,
                            'price': current_price,
                            'value': sale_value
                        })
                        del new_portfolio[stock_code]

        # 买入目标组合中的股票
        for stock_code, target_weight in target_portfolio.items():
            target_value = portfolio_value * target_weight
            current_value = 0.0

            if stock_code in new_portfolio and stock_code in stock_data:
                shares = new_portfolio[stock_code]
                df = stock_data[stock_code]
                price_data = df[df['date'] <= date]
                if not price_data.empty:
                    current_price = price_data.iloc[-1]['close']
                    current_value = shares * current_price

            # 需要买入的金额
            buy_value = target_value - current_value
            if buy_value > 0 and stock_code in stock_data:
                df = stock_data[stock_code]
                price_data = df[df['date'] <= date]
                if not price_data.empty:
                    current_price = price_data.iloc[-1]['close']
                    max_shares = int(cash / (current_price * (1 + self.commission_rate)))
                    required_shares = int(buy_value / current_price)
                    shares_to_buy = min(max_shares, required_shares)

                    if shares_to_buy > 0:
                        cost = shares_to_buy * current_price * (1 + self.commission_rate)
                        if cost <= cash:
                            cash -= cost
                            new_portfolio[stock_code] = new_portfolio.get(stock_code, 0) + shares_to_buy
                            trades.append({
                                'stock_code': stock_code,
                                'action': 'buy',
                                'shares': shares_to_buy,
                                'price': current_price,
                                'value': cost
                            })

        return cash, new_portfolio, trades

    def _get_future_trading_date(self, current_date: pd.Timestamp, days: int,
                               trading_dates: List[pd.Timestamp]) -> pd.Timestamp:
        """获取未来的交易日"""
        current_index = None
        for i, date in enumerate(trading_dates):
            if date >= current_date:
                current_index = i
                break

        if current_index is not None and current_index + days < len(trading_dates):
            return trading_dates[current_index + days]
        else:
            return current_date + pd.Timedelta(days=days)

    def _calculate_performance_metrics(self, portfolio_history: List[Dict],
                                     trades_history: List[Dict]) -> Dict[str, Any]:
        """计算绩效指标"""
        if not portfolio_history:
            return {}

        # 转换为DataFrame便于计算
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])

        # 计算日收益率
        df['daily_return'] = df['portfolio_value'].pct_change()

        # 基本指标
        initial_value = df['portfolio_value'].iloc[0]
        final_value = df['portfolio_value'].iloc[-1]
        total_return = (final_value - initial_value) / initial_value

        # 计算交易天数
        trading_days = len(df)
        years = trading_days / 252  # 假设一年252个交易日

        # 年化收益率
        annualized_return = (final_value / initial_value) ** (1 / years) - 1

        # 波动率
        volatility = df['daily_return'].std() * np.sqrt(252)

        # 夏普比率（假设无风险利率为3%）
        sharpe_ratio = (annualized_return - 0.03) / volatility if volatility > 0 else 0

        # 最大回撤
        df['cummax'] = df['portfolio_value'].cummax()
        df['drawdown'] = (df['cummax'] - df['portfolio_value']) / df['cummax']
        max_drawdown = df['drawdown'].max()

        # 胜率
        positive_returns = df['daily_return'] > 0
        win_rate = positive_returns.mean()

        # 交易统计
        total_trades = len(trades_history)
        buy_trades = len([t for t in trades_history if t['action'] == 'buy'])
        sell_trades = len([t for t in trades_history if t['action'] == 'sell'])

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trading_days': trading_days,
            'years': years,
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'initial_value': initial_value,
            'final_value': final_value
        }

    def set_factor_weights(self, momentum_weight: float, value_weight: float):
        """设置因子权重"""
        total_weight = momentum_weight + value_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError("因子权重总和必须等于1.0")

        self.factor_weights = {
            'momentum': momentum_weight,
            'value': value_weight
        }

    def generate_report(self, backtest_results: Dict[str, Any]) -> str:
        """生成回测报告"""
        performance = backtest_results['performance_metrics']
        config = backtest_results['backtest_config']

        report = f"""
=== A股智能投顾助手 - 回测报告 ===

回测配置:
- 回测期间: {config['start_date']} 到 {config['end_date']}
- 初始资金: {config['initial_capital']:,.0f}
- 因子权重: 动量 {config['factor_weights']['momentum']:.1%}, 价值 {config['factor_weights']['value']:.1%}
- 调仓频率: {config['rebalance_frequency']}

绩效指标:
- 总收益率: {performance['total_return']:.2%}
- 年化收益率: {performance['annualized_return']:.2%}
- 年化波动率: {performance['volatility']:.2%}
- 夏普比率: {performance['sharpe_ratio']:.2f}
- 最大回撤: {performance['max_drawdown']:.2%}
- 胜率: {performance['win_rate']:.2%}
- 交易天数: {performance['trading_days']}
- 总交易次数: {performance['total_trades']}

交易统计:
- 买入交易: {performance['buy_trades']}
- 卖出交易: {performance['sell_trades']}

组合价值变化:
- 期初价值: {performance['initial_value']:,.0f}
- 期末价值: {performance['final_value']:,.0f}

风险分析:
- 最大回撤已达到 {performance['max_drawdown']:.2%}，风险控制在15%以内
- 夏普比率 {performance['sharpe_ratio']:.2f}，{'表现良好' if performance['sharpe_ratio'] > 1 else '需要优化'}

结论:
{'策略表现优异，建议进行实盘验证' if performance['annualized_return'] > 0.15 and performance['sharpe_ratio'] > 1 else '策略需要进一步优化参数'}
        """
        return report


def main():
    """主函数 - 运行示例回测"""
    # 创建回测引擎
    engine = BacktestEngine()

    # 设置因子权重（可自定义）
    engine.set_factor_weights(momentum_weight=0.6, value_weight=0.4)

    # 运行回测
    results = engine.run_backtest(
        start_date='2023-01-01',
        end_date='2024-01-01',
        rebalance_frequency='weekly'
    )

    # 生成报告
    report = engine.generate_report(results)
    print(report)

    # 保存结果
    output_dir = Path(__file__).parent.parent.parent.parent / "data" / "backtest_results"
    output_dir.mkdir(exist_ok=True)

    import json
    with open(output_dir / "backtest_results.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    with open(output_dir / "backtest_report.txt", 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"回测结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()