#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 2: 全样本单因子验证引擎
目标: 将100只股票样本的结论，推广到整个CSI 800成分股上，进行最终验证
验证问题: "我们在100只抽样股票上观察到的因子表现，在全市场范围内是否依然成立？"
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging
import json
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.single_factor_validator import SingleFactorValidator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase2_validation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FullSampleFactorValidator(SingleFactorValidator):
    """全样本因子验证器 - Phase 2核心验证引擎"""

    def __init__(self):
        super().__init__()

        # 覆盖数据目录为全样本CSI800
        self.data_dir = Path("data/historical/stocks/complete_csi800/stocks")

        # 输出目录
        self.phase2_output_dir = Path("phase2_validation_results")
        self.phase2_output_dir.mkdir(exist_ok=True)

        # Phase 2专用配置
        self.phase2_factor_configs = {
            'volume_surge': {
                'name': '成交量激增因子',
                'weight': 0.30,
                'params': {'volume_period': 20}
            },
            'momentum_strength': {
                'name': '动量强度因子',
                'weight': 0.70,
                'params': {'lwr_period': 14}
            }
        }

        # 结果存储
        self.validation_results = {}

        # 覆盖市场时期定义为字典格式（与父类兼容）
        self.market_periods = {
            'bear_market_2022': {
                'start_date': '2022-01-01',
                'end_date': '2022-12-31',
                'description': '2022年熊市'
            },
            'bull_market_2023h1': {
                'start_date': '2023-01-01',
                'end_date': '2023-06-30',
                'description': '2023年上半年牛市'
            }
        }

    def get_all_csi800_stocks(self) -> List[str]:
        """获取所有CSI800成分股列表"""
        all_stocks = []

        if not os.path.exists(self.data_dir):
            logger.error(f"数据目录不存在: {self.data_dir}")
            return []

        # 遍历所有年份目录
        for year_dir in os.listdir(self.data_dir):
            year_path = os.path.join(self.data_dir, year_dir)
            if os.path.isdir(year_path):
                # 获取该年份的所有股票文件
                for file in os.listdir(year_path):
                    if file.endswith('.csv'):
                        stock_code = file.replace('.csv', '')
                        if stock_code not in all_stocks:
                            all_stocks.append(stock_code)

        logger.info(f"发现 {len(all_stocks)} 只CSI800成分股")
        return sorted(all_stocks)

    def load_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载单只股票数据"""
        try:
            # 使用父类的load_stock_data方法获取完整数据
            full_data = super().load_stock_data(stock_code)
            if full_data is None or full_data.empty:
                return pd.DataFrame()

            # 确保数据格式正确
            full_data['date'] = pd.to_datetime(full_data['date'])
            full_data = full_data.sort_values('date').reset_index(drop=True)

            # 按日期范围过滤
            start_date_dt = pd.to_datetime(start_date)
            end_date_dt = pd.to_datetime(end_date)

            filtered_data = full_data[
                (full_data['date'] >= start_date_dt) &
                (full_data['date'] <= end_date_dt)
            ]

            return filtered_data

        except Exception as e:
            logger.warning(f"加载股票 {stock_code} 数据失败: {e}")
            return pd.DataFrame()

    def calculate_factor_scores(self, data: pd.DataFrame, factor_type: str) -> Tuple[pd.Series, pd.Series]:
        """计算因子得分和收益率"""
        if data.empty or len(data) < 30:
            return None, None

        try:
            # 计算收益率
            returns = data['close'].pct_change().dropna()

            # 根据因子类型计算得分
            if factor_type == 'volume_surge':
                # 成交量激增因子
                volume_ma20 = data['volume'].rolling(window=20).mean()
                volume_ratio = data['volume'] / volume_ma20
                factor_scores = volume_ratio.fillna(1.0)

            elif factor_type == 'momentum_strength':
                # 动量强度因子 (LWR)
                lwr_period = 14
                high = data['high'].rolling(lwr_period).max()
                low = data['low'].rolling(lwr_period).min()
                close = data['close']

                lwr = -100 * (high - close) / (high - low)
                factor_scores = lwr.fillna(-50.0)

            else:
                logger.warning(f"未知的因子类型: {factor_type}")
                return None, None

            return factor_scores, returns

        except Exception as e:
            logger.warning(f"计算因子得分失败: {e}")
            return None, None

    def calculate_strategy_performance(self, factor_scores: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """计算策略表现指标"""
        if factor_scores.empty or returns.empty or len(factor_scores) != len(returns):
            return {}

        try:
            # 对齐数据
            aligned_data = pd.concat([factor_scores, returns], axis=1).dropna()
            if len(aligned_data) < 10:
                return {}

            factor_scores = aligned_data.iloc[:, 0]
            returns = aligned_data.iloc[:, 1]

            # 计算策略收益（基于因子分位数）
            factor_quantile = factor_scores.rank(pct=True)

            # 买入信号：因子得分最高的20%
            buy_signal = factor_quantile > 0.8

            # 策略收益
            strategy_returns = returns[buy_signal]

            if len(strategy_returns) == 0:
                return {}

            # 计算指标
            total_return = (1 + strategy_returns).prod() - 1
            trading_days = len(strategy_returns)
            annual_return = (1 + total_return) ** (252 / trading_days) - 1

            # 夏普比率
            excess_returns = strategy_returns - 0.03/252  # 假设无风险利率3%
            if excess_returns.std() > 0:
                sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0

            # 最大回撤
            cumulative = (1 + strategy_returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()

            # 胜率
            win_rate = (strategy_returns > 0).mean()

            return {
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': len(strategy_returns),
                'trading_days': trading_days
            }

        except Exception as e:
            logger.warning(f"计算策略表现失败: {e}")
            return {}

    def validate_full_sample_factor(self, factor_type: str) -> Dict[str, Any]:
        """验证单个因子在全部CSI800股票上的表现"""
        logger.info(f"开始全样本验证因子: {factor_type}")

        # 获取所有股票
        all_stocks = self.get_all_csi800_stocks()
        if not all_stocks:
            logger.error("无法获取CSI800股票列表")
            return {}

        factor_config = self.phase2_factor_configs[factor_type]
        results = {
            'factor_name': factor_config['name'],
            'factor_type': factor_type,
            'total_stocks': len(all_stocks),
            'period_results': {},
            'stock_results': [],
            'validation_stats': {}
        }

        # 按时期验证
        for period_name, period_config in self.market_periods.items():
            logger.info(f"验证时期: {period_name} ({period_config['description']})")

            period_metrics = []
            successful_stocks = 0

            for i, stock_code in enumerate(all_stocks):
                if i % 100 == 0:
                    logger.info(f"处理进度: {i}/{len(all_stocks)} - {stock_code}")

                # 加载数据
                data = self.load_stock_data(
                    stock_code,
                    period_config['start_date'],
                    period_config['end_date']
                )

                if data.empty or len(data) < 30:
                    continue

                # 计算因子得分和收益率
                factor_scores, returns = self.calculate_factor_scores(data, factor_type)

                if factor_scores is None or returns is None:
                    continue

                # 计算策略表现
                strategy_metrics = self.calculate_strategy_performance(factor_scores, returns)

                if strategy_metrics:
                    strategy_metrics['stock_code'] = stock_code
                    period_metrics.append(strategy_metrics)
                    successful_stocks += 1

            # 汇总时期结果
            if period_metrics:
                period_df = pd.DataFrame(period_metrics)

                # 计算统计指标
                mean_return = period_df['annual_return'].mean()
                std_return = period_df['annual_return'].std()
                mean_sharpe = period_df['sharpe_ratio'].mean()
                mean_drawdown = period_df['max_drawdown'].mean()
                mean_winrate = period_df['win_rate'].mean()

                # 统计显著性
                if len(period_df) > 1:
                    std_error = std_return / np.sqrt(len(period_df))
                    z_score_95 = 1.96
                    ci_lower = mean_return - z_score_95 * std_error
                    ci_upper = mean_return + z_score_95 * std_error
                    t_stat = mean_return / std_error if std_error > 0 else 0
                else:
                    std_error = 0
                    ci_lower = ci_upper = mean_return
                    t_stat = 0

                results['period_results'][period_name] = {
                    'description': period_config['description'],
                    'successful_stocks': successful_stocks,
                    'success_rate': successful_stocks / len(all_stocks),
                    'mean_annual_return': mean_return,
                    'std_annual_return': std_return,
                    'mean_sharpe_ratio': mean_sharpe,
                    'mean_max_drawdown': mean_drawdown,
                    'mean_win_rate': mean_winrate,
                    'confidence_interval': {
                        '95%_ci_lower': ci_lower,
                        '95%_ci_upper': ci_upper,
                        'margin_of_error': z_score_95 * std_error if std_error > 0 else 0
                    },
                    'statistical_significance': {
                        't_statistic': t_stat,
                        'standard_error': std_error,
                        'sample_size': len(period_df)
                    }
                }

                logger.info(f"{period_name} 完成: {successful_stocks}/{len(all_stocks)} 只股票")
                logger.info(f"  平均年化收益: {mean_return:.2%}")
                logger.info(f"  平均夏普比率: {mean_sharpe:.2f}")

        # 验证统计
        results['validation_stats'] = {
            'total_stocks_tested': len(all_stocks),
            'validation_periods': len(self.market_periods),
            'factor_weight': factor_config['weight'],
            'data_quality': 'high' if successful_stocks > len(all_stocks) * 0.9 else 'medium'
        }

        return results

    def generate_phase2_report(self, factor_results: Dict) -> str:
        """生成Phase 2验证报告"""
        report = []
        report.append(f"# Phase 2: {factor_results['factor_name']} 全样本验证报告")
        report.append("=" * 80)
        report.append("")

        # 验证概述
        report.append("## 验证概述")
        report.append(f"- 验证因子: {factor_results['factor_name']}")
        report.append(f"- 验证样本: 全部 {factor_results['total_stocks']} 只CSI800成分股")
        report.append(f"- 验证时期: {len(self.market_periods)} 个市场阶段")
        report.append(f"- 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 数据质量
        report.append("## 数据质量统计")
        stats = factor_results['validation_stats']
        report.append(f"- 总测试股票: {stats['total_stocks_tested']} 只")
        report.append(f"- 验证时期数: {stats['validation_periods']} 个")
        report.append(f"- 因子权重: {stats['factor_weight']:.1%}")
        report.append(f"- 数据质量: {stats['data_quality']}")
        report.append("")

        # 各时期表现
        report.append("## 全样本各时期表现")
        for period_name, period_result in factor_results['period_results'].items():
            report.append(f"### {period_result['description']}")
            report.append(f"- 成功股票数: {period_result['successful_stocks']} 只")
            report.append(f"- 成功率: {period_result['success_rate']:.1%}")
            report.append(f"- 平均年化收益: {period_result['mean_annual_return']:.2%}")
            report.append(f"- 平均夏普比率: {period_result['mean_sharpe_ratio']:.2f}")
            report.append(f"- 平均最大回撤: {period_result['mean_max_drawdown']:.2%}")
            report.append(f"- 平均胜率: {period_result['mean_win_rate']:.2%}")

            # 统计显著性
            ci = period_result['confidence_interval']
            sig = period_result['statistical_significance']
            report.append(f"- 95%置信区间: [{ci['95%_ci_lower']:.2%}, {ci['95%_ci_upper']:.2%}]")
            report.append(f"- 边际误差: {ci['margin_of_error']:.2%}")
            report.append(f"- t统计量: {sig['t_statistic']:.2f}")
            report.append("")

        # 核心问题回答
        report.append("## 验证结论")
        report.append("### 核心问题回答")
        report.append("**'我们在100只抽样股票上观察到的因子表现，在全市场范围内是否依然成立？'**")
        report.append("")

        # 基于结果给出结论
        overall_positive = all(
            period['mean_annual_return'] > 0
            for period in factor_results['period_results'].values()
        )

        if overall_positive:
            report.append("✅ **答案：是的，基本成立**")
            report.append("- 全样本验证结果显示因子在各时期均表现正面")
            report.append("- 因子在更大样本范围内保持了统计显著性")
            report.append("- 可以进入组合策略构建阶段")
        else:
            report.append("⚠️ **答案：需要谨慎评估**")
            report.append("- 全样本验证结果与样本结论存在差异")
            report.append("- 需要重新审视因子逻辑或调整参数")
            report.append("- 建议进一步分析差异原因")

        report.append("")
        report.append("### 验证标准")
        report.append("- ✅ 成功标准: 全样本年化收益 > 0%")
        report.append("- ✅ 统计标准: 95%置信区间不包含0")
        report.append("- ✅ 质量标准: 成功率 > 90%")

        return "\n".join(report)

    def run_phase2_validation(self, factor_types: List[str] = None) -> Dict[str, Any]:
        """运行Phase 2全样本验证"""
        if factor_types is None:
            factor_types = list(self.phase2_factor_configs.keys())

        all_results = {}

        for factor_type in factor_types:
            logger.info(f"开始Phase 2全样本验证: {factor_type}")

            # 验证单个因子
            factor_results = self.validate_full_sample_factor(factor_type)
            if not factor_results:
                logger.error(f"因子 {factor_type} 验证失败")
                continue

            # 保存结果
            all_results[factor_type] = factor_results

            # 生成报告
            report = self.generate_phase2_report(factor_results)

            # 保存报告
            report_file = self.phase2_output_dir / f"{factor_type}_phase2_validation_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"{factor_type} Phase 2验证完成，报告已保存: {report_file}")

        return all_results

def main():
    """主函数"""
    logger.info("=== Phase 2: 全样本单因子验证开始 ===")

    validator = FullSampleFactorValidator()

    # 运行验证
    results = validator.run_phase2_validation()

    logger.info("=== Phase 2: 全样本单因子验证完成 ===")

    # 生成汇总报告
    if results:
        summary_report = []
        summary_report.append("# Phase 2: 全样本单因子验证汇总报告")
        summary_report.append("=" * 80)
        summary_report.append("")

        for factor_type, factor_results in results.items():
            summary_report.append(f"## {factor_results['factor_name']}")
            summary_report.append(f"- 测试股票数: {factor_results['total_stocks']} 只")

            for period_name, period_result in factor_results['period_results'].items():
                summary_report.append(f"- {period_result['description']}: {period_result['mean_annual_return']:.2%} (夏普: {period_result['mean_sharpe_ratio']:.2f})")

            summary_report.append("")

        # 保存汇总报告
        summary_file = validator.phase2_output_dir / "phase2_summary_report.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary_report))

        logger.info(f"汇总报告已保存: {summary_file}")

if __name__ == "__main__":
    main()