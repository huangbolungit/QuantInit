#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单因子验证框架 - Phase 1 Implementation
专门用于验证各个独立因子的有效性和市场适应性
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('single_factor_validation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SingleFactorValidator:
    """
    单因子验证器 - 专注于独立因子的有效性验证
    """

    def __init__(self):
        # 使用完整的CSI800数据
        self.data_dir = Path("data/historical/stocks/complete_csi800/stocks")
        self.output_dir = Path("factor_validation_results")
        self.output_dir.mkdir(exist_ok=True)

        # 市场分段定义
        self.market_periods = {
            'bear_market_2022': ('2022-01-01', '2022-12-31'),
            'bull_market_2023h1': ('2023-01-01', '2023-06-30')
        }

        # 固定参数设置
        self.ma_short_window = 5
        self.ma_long_window = 20
        self.volume_ma_window = 20
        self.lwr_period = 14

        logger.info("单因子验证器初始化完成")

    def load_stock_data(self, stock_code: str) -> Optional[pd.DataFrame]:
        """加载单只股票的完整历史数据"""
        all_data = []

        # 遍历所有年份目录
        for year_dir in sorted(self.data_dir.glob("*")):
            if not year_dir.is_dir():
                continue

            year = year_dir.name
            if not year.isdigit():
                continue

            stock_file = year_dir / f"{stock_code}.csv"
            if stock_file.exists():
                try:
                    df = pd.read_csv(stock_file)
                    df['date'] = pd.to_datetime(df['date'])
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"读取 {stock_code} {year}年数据失败: {e}")

        if not all_data:
            logger.warning(f"未找到股票 {stock_code} 的数据")
            return None

        # 合并所有年份数据
        combined_data = pd.concat(all_data, ignore_index=True)
        combined_data = combined_data.sort_values('date').reset_index(drop=True)

        # 数据清理
        combined_data = combined_data.dropna()
        combined_data = combined_data.drop_duplicates(subset=['date'])

        logger.info(f"加载 {stock_code} 数据完成: {len(combined_data)} 条记录")
        return combined_data

    def calculate_ma_arrangement_score(self, data: pd.DataFrame) -> pd.Series:
        """
        均线排列因子 - 固定20日窗口
        评分逻辑: MA5 > MA20 时得分为1，否则为0
        """
        ma5 = data['close'].rolling(window=self.ma_short_window).mean()
        ma20 = data['close'].rolling(window=self.ma_long_window).mean()

        # 均线排列得分 (1或0)
        arrangement_score = np.where(ma5 > ma20, 1, 0)

        return pd.Series(arrangement_score, index=data.index)

    def calculate_sector_relative_strength(self, data: pd.DataFrame) -> pd.Series:
        """
        板块相对强度因子 - 相对CSI800基准的表现
        评分逻辑: 相对强度越高，得分越高
        """
        # 简化版本：使用价格动量作为相对强度代理
        # 实际应用中需要板块指数数据进行对比

        # 计算20日收益率作为相对强度指标
        returns_20d = data['close'].pct_change(periods=self.ma_long_window)

        # 标准化得分 (0-100)
        # 使用历史百分位数进行标准化
        score = (returns_20d - returns_20d.quantile(0.1)) / (returns_20d.quantile(0.9) - returns_20d.quantile(0.1)) * 100
        score = np.clip(score, 0, 100)

        return score.fillna(0)

    def calculate_volume_surge_factor(self, data: pd.DataFrame) -> pd.Series:
        """
        成交量激增因子 - 固定20日平均
        计算方法: Volume Ratio = Today's Volume / 20-day Average Volume
        评分逻辑: 比率越高，得分越高
        """
        volume_ma20 = data['volume'].rolling(window=self.volume_ma_window).mean()
        volume_ratio = data['volume'] / volume_ma20

        # 评分逻辑
        score = np.where(volume_ratio >= 2.5, 100,
                         np.where(volume_ratio >= 2.0, 80,
                         np.where(volume_ratio >= 1.5, 60,
                         np.where(volume_ratio >= 1.2, 40,
                         np.where(volume_ratio >= 1.0, 20, 0)))))

        return pd.Series(score, index=data.index)

    def calculate_lwr_factor(self, data: pd.DataFrame) -> pd.Series:
        """
        动量强度因子 (LWR) - 固定14日周期
        计算方法: 14日LWR指标，值域-100到0
        评分逻辑: LWR越接近0(超买)，动量越强，得分越高
        """
        # 计算最高价和最低价的14日滚动最大最小值
        highest_high = data['high'].rolling(window=self.lwr_period).max()
        lowest_low = data['low'].rolling(window=self.lwr_period).min()

        # 计算LWR指标
        lwr = (highest_high - data['close']) / (highest_high - lowest_low) * -100

        # 评分逻辑 (LWR越接近0得分越高)
        score = np.where(lwr >= -20, 100,
                        np.where(lwr >= -40, 80,
                        np.where(lwr >= -60, 60,
                        np.where(lwr >= -80, 40, 0))))

        return pd.Series(score, index=data.index)

    def calculate_strategy_returns(self, data: pd.DataFrame, factor_scores: pd.Series) -> pd.Series:
        """基于因子得分计算策略收益率"""
        # 生成交易信号：因子得分 > 50 时买入
        signals = (factor_scores > 50).astype(int)

        # 计算下一日收益率
        returns = data['close'].pct_change().shift(-1)

        # 策略收益率 = 信号 * 下一日收益率
        strategy_returns = signals * returns

        return strategy_returns.fillna(0)

    def calculate_performance_metrics(self, returns: pd.Series, period_name: str = "") -> Dict[str, float]:
        """计算绩效指标"""
        if len(returns) == 0:
            return {}

        # 年化收益率
        annual_return = returns.mean() * 252

        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252)

        # 夏普比率 (无风险利率假设为0)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0

        # 最大回撤
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (returns > 0).mean()

        metrics = {
            'period': period_name,
            'total_days': len(returns),
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }

        return metrics

    def filter_data_by_period(self, data: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """按时间段过滤数据"""
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        mask = (data['date'] >= start_date) & (data['date'] <= end_date)
        return data[mask].reset_index(drop=True)

    def validate_single_factor(self, factor_name: str, sample_stocks: List[str] = None) -> Dict[str, Any]:
        """单个因子完整验证"""
        logger.info(f"开始验证因子: {factor_name}")

        if sample_stocks is None:
            # 使用部分股票进行测试
            sample_stocks = ['000001', '000002', '600000', '600036', '600519']

        # 因子计算函数映射
        factor_functions = {
            'ma_arrangement': self.calculate_ma_arrangement_score,
            'sector_strength': self.calculate_sector_relative_strength,
            'volume_surge': self.calculate_volume_surge_factor,
            'momentum_strength': self.calculate_lwr_factor
        }

        if factor_name not in factor_functions:
            raise ValueError(f"未知因子: {factor_name}")

        factor_func = factor_functions[factor_name]

        results = {
            'factor_name': factor_name,
            'period_results': {},
            'overall_metrics': {},
            'stock_results': []
        }

        # 验证每个市场时期
        for period_name, (start_date, end_date) in self.market_periods.items():
            logger.info(f"验证时期: {period_name} ({start_date} 到 {end_date})")

            period_returns = []

            for stock_code in sample_stocks:
                try:
                    # 加载股票数据
                    stock_data = self.load_stock_data(stock_code)
                    if stock_data is None:
                        continue

                    # 按时期过滤数据
                    period_data = self.filter_data_by_period(stock_data, start_date, end_date)
                    if len(period_data) < 20:  # 数据不足
                        continue

                    # 计算因子得分
                    factor_scores = factor_func(period_data)

                    # 计算策略收益率
                    strategy_returns = self.calculate_strategy_returns(period_data, factor_scores)

                    period_returns.append(strategy_returns)

                    # 保存单股票结果
                    stock_metrics = self.calculate_performance_metrics(strategy_returns, f"{period_name}_{stock_code}")
                    results['stock_results'].append({
                        'stock': stock_code,
                        'period': period_name,
                        'metrics': stock_metrics,
                        'total_days': len(strategy_returns)
                    })

                except Exception as e:
                    logger.warning(f"处理股票 {stock_code} 在时期 {period_name} 时出错: {e}")

            # 计算时期整体指标
            if period_returns:
                all_returns = pd.concat(period_returns, ignore_index=True)
                period_metrics = self.calculate_performance_metrics(all_returns, period_name)
                results['period_results'][period_name] = period_metrics

        # 计算总体指标
        all_stock_returns = []
        for stock_result in results['stock_results']:
            if stock_result['metrics']:
                # 这里简化处理，实际应该重新计算收益率
                pass

        logger.info(f"因子 {factor_name} 验证完成")
        return results

    def generate_factor_report(self, factor_results: Dict[str, Any]) -> str:
        """生成因子验证报告"""
        report = []
        report.append(f"# {factor_results['factor_name']} 因子验证报告")
        report.append("=" * 50)
        report.append("")

        # 各时期表现
        report.append("## 各时期表现")
        report.append("")
        for period, metrics in factor_results['period_results'].items():
            report.append(f"### {period}")
            report.append(f"- 年化收益率: {metrics['annual_return']:.2%}")
            report.append(f"- 夏普比率: {metrics['sharpe_ratio']:.2f}")
            report.append(f"- 最大回撤: {metrics['max_drawdown']:.2%}")
            report.append(f"- 胜率: {metrics['win_rate']:.2%}")
            report.append(f"- 交易天数: {metrics['total_days']}")
            report.append("")

        # 权重分配建议
        report.append("## 权重分配建议")
        report.append("")

        # 基于夏普比率的权重计算
        total_sharpe = sum(metrics.get('sharpe_ratio', 0) for metrics in factor_results['period_results'].values())
        if total_sharpe > 0:
            for period, metrics in factor_results['period_results'].items():
                weight = metrics.get('sharpe_ratio', 0) / total_sharpe
                report.append(f"- {period}: {weight:.1%}")

        return "\n".join(report)

    def run_all_factor_validation(self) -> Dict[str, Any]:
        """运行所有因子的验证"""
        factors = ['ma_arrangement', 'sector_strength', 'volume_surge', 'momentum_strength']

        all_results = {}

        for factor in factors:
            try:
                results = self.validate_single_factor(factor)
                all_results[factor] = results

                # 生成报告
                report = self.generate_factor_report(results)

                # 保存报告
                report_file = self.output_dir / f"{factor}_validation_report.md"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)

                logger.info(f"因子 {factor} 报告已保存: {report_file}")

            except Exception as e:
                logger.error(f"验证因子 {factor} 时出错: {e}")

        return all_results


def main():
    """主函数"""
    validator = SingleFactorValidator()

    logger.info("开始 Phase 1: 单因子验证")

    # 运行所有因子验证
    results = validator.run_all_factor_validation()

    logger.info("Phase 1: 单因子验证完成")

    # 生成综合报告
    summary_report = []
    summary_report.append("# Phase 1: 单因子验证综合报告")
    summary_report.append("=" * 50)
    summary_report.append("")

    for factor_name, factor_results in results.items():
        summary_report.append(f"## {factor_name}")

        for period, metrics in factor_results['period_results'].items():
            summary_report.append(f"- {period}: 夏普比率 {metrics['sharpe_ratio']:.2f}, 年化收益 {metrics['annual_return']:.2%}")

        summary_report.append("")

    # 保存综合报告
    summary_file = validator.output_dir / "phase1_summary_report.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(summary_report))

    logger.info(f"综合报告已保存: {summary_file}")


if __name__ == "__main__":
    main()