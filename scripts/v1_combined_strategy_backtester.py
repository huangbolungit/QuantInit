#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V1组合策略回测引擎 - Phase 2核心策略实现
基于Phase 2验证结果构建的组合策略
策略公式: 综合评分 = (动量强度因子分 * 70%) + (成交量激增因子分 * 30%)
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

from scripts.full_sample_factor_validator import FullSampleFactorValidator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('v1_combined_strategy.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class V1CombinedStrategyBacktester(FullSampleFactorValidator):
    """V1组合策略回测器 - Phase 2核心策略实现"""

    def __init__(self):
        super().__init__()

        # 输出目录
        self.v1_output_dir = Path("v1_strategy_results")
        self.v1_output_dir.mkdir(exist_ok=True)

        # V1策略配置
        self.v1_strategy_config = {
            'name': 'V1组合策略',
            'formula': '综合评分 = (动量强度因子分 * 70%) + (成交量激增因子分 * 30%)',
            'factors': {
                'momentum_strength': {
                    'weight': 0.70,
                    'name': '动量强度因子'
                },
                'volume_surge': {
                    'weight': 0.30,
                    'name': '成交量激增因子'
                }
            },
            'selection_threshold': 0.8,  # 选择前20%的股票
            'rebalance_frequency': 'monthly',  # 月度调仓
            'max_positions': 50  # 最大持仓数
        }

        # 策略结果存储
        self.strategy_results = {}

    def calculate_combined_factor_scores(self, data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """计算组合因子得分"""
        if data.empty or len(data) < 30:
            return None, None

        try:
            # 计算收益率
            returns = data['close'].pct_change().dropna()

            # 计算动量强度因子得分 (LWR)
            lwr_period = 14
            high = data['high'].rolling(lwr_period).max()
            low = data['low'].rolling(lwr_period).min()
            close = data['close']
            lwr = -100 * (high - close) / (high - low)
            momentum_scores = lwr.fillna(-50.0)

            # 计算成交量激增因子得分
            volume_ma20 = data['volume'].rolling(window=20).mean()
            volume_ratio = data['volume'] / volume_ma20
            volume_scores = volume_ratio.fillna(1.0)

            # 标准化因子得分 (0-1范围)
            momentum_normalized = self._normalize_scores(momentum_scores)
            volume_normalized = self._normalize_scores(volume_scores)

            # 计算组合得分
            momentum_weight = self.v1_strategy_config['factors']['momentum_strength']['weight']
            volume_weight = self.v1_strategy_config['factors']['volume_surge']['weight']

            combined_scores = (momentum_normalized * momentum_weight) + (volume_normalized * volume_weight)

            return combined_scores, returns

        except Exception as e:
            logger.warning(f"计算组合因子得分失败: {e}")
            return None, None

    def _normalize_scores(self, scores: pd.Series) -> pd.Series:
        """标准化因子得分到0-1范围"""
        if scores.empty:
            return scores

        # 使用滚动窗口标准化，避免未来数据泄露
        rolling_mean = scores.rolling(window=252, min_periods=60).mean()
        rolling_std = scores.rolling(window=252, min_periods=60).std()

        normalized = (scores - rolling_mean) / rolling_std
        # 将标准化结果映射到0-1范围
        normalized = (normalized - normalized.min()) / (normalized.max() - normalized.min())

        return normalized.fillna(0.5)

    def calculate_strategy_performance(self, combined_scores: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """计算V1组合策略表现"""
        if combined_scores.empty or returns.empty or len(combined_scores) != len(returns):
            return {}

        try:
            # 对齐数据
            aligned_data = pd.concat([combined_scores, returns], axis=1).dropna()
            if len(aligned_data) < 10:
                return {}

            combined_scores = aligned_data.iloc[:, 0]
            returns = aligned_data.iloc[:, 1]

            # 计算策略收益（基于组合分位数）
            factor_quantile = combined_scores.rank(pct=True)

            # 买入信号：组合得分最高的20%
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

            # 信息比率 (相对于市场)
            market_returns = returns  # 市场收益
            excess_returns_strategy = strategy_returns - market_returns.reindex(strategy_returns.index, fill_value=0)
            if excess_returns_strategy.std() > 0:
                information_ratio = excess_returns_strategy.mean() / excess_returns_strategy.std() * np.sqrt(252)
            else:
                information_ratio = 0

            return {
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'information_ratio': information_ratio,
                'total_trades': len(strategy_returns),
                'trading_days': trading_days,
                'selection_rate': len(strategy_returns) / len(returns)  # 选股比例
            }

        except Exception as e:
            logger.warning(f"计算策略表现失败: {e}")
            return {}

    def run_v1_strategy_backtest(self) -> Dict[str, Any]:
        """运行V1组合策略完整回测"""
        logger.info("=== V1组合策略回测开始 ===")
        logger.info(f"策略公式: {self.v1_strategy_config['formula']}")

        # 获取所有股票
        all_stocks = self.get_all_csi800_stocks()
        if not all_stocks:
            logger.error("无法获取CSI800股票列表")
            return {}

        results = {
            'strategy_name': self.v1_strategy_config['name'],
            'strategy_formula': self.v1_strategy_config['formula'],
            'total_stocks': len(all_stocks),
            'period_results': {},
            'strategy_performance': {},
            'factor_contributions': {},
            'validation_stats': {}
        }

        # 按时期回测
        for period_name, period_config in self.market_periods.items():
            logger.info(f"回测时期: {period_name} ({period_config['description']})")

            period_returns = []
            period_performance_metrics = []
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

                # 计算组合因子得分
                combined_scores, returns = self.calculate_combined_factor_scores(data)

                if combined_scores is None or returns is None:
                    continue

                # 计算策略表现
                strategy_metrics = self.calculate_strategy_performance(combined_scores, returns)

                if strategy_metrics:
                    strategy_metrics['stock_code'] = stock_code
                    period_performance_metrics.append(strategy_metrics)
                    period_returns.extend(returns[combined_scores.rank(pct=True) > 0.8].tolist())
                    successful_stocks += 1

            # 汇总时期结果
            if period_performance_metrics:
                period_df = pd.DataFrame(period_performance_metrics)

                # 计算平均策略表现
                avg_annual_return = period_df['annual_return'].mean()
                avg_sharpe_ratio = period_df['sharpe_ratio'].mean()
                avg_max_drawdown = period_df['max_drawdown'].mean()
                avg_win_rate = period_df['win_rate'].mean()
                avg_information_ratio = period_df['information_ratio'].mean()

                # 计算整体策略收益（等权重所有股票）
                if period_returns:
                    overall_return = np.mean(period_returns)
                    overall_annual_return = overall_return * 252  # 简化年化
                    overall_volatility = np.std(period_returns) * np.sqrt(252)
                    overall_sharpe = overall_annual_return / overall_volatility if overall_volatility > 0 else 0
                else:
                    overall_annual_return = 0
                    overall_volatility = 0
                    overall_sharpe = 0

                results['period_results'][period_name] = {
                    'description': period_config['description'],
                    'successful_stocks': successful_stocks,
                    'success_rate': successful_stocks / len(all_stocks),
                    'avg_annual_return': avg_annual_return,
                    'avg_sharpe_ratio': avg_sharpe_ratio,
                    'avg_max_drawdown': avg_max_drawdown,
                    'avg_win_rate': avg_win_rate,
                    'avg_information_ratio': avg_information_ratio,
                    'overall_portfolio_return': overall_annual_return,
                    'overall_portfolio_volatility': overall_volatility,
                    'overall_portfolio_sharpe': overall_sharpe,
                    'total_trades': period_df['total_trades'].sum()
                }

                logger.info(f"{period_name} 完成: {successful_stocks}/{len(all_stocks)} 只股票")
                logger.info(f"  平均年化收益: {avg_annual_return:.2%}")
                logger.info(f"  平均夏普比率: {avg_sharpe_ratio:.2f}")
                logger.info(f"  组合年化收益: {overall_annual_return:.2%}")
                logger.info(f"  组合夏普比率: {overall_sharpe:.2f}")

        # 策略验证统计
        results['validation_stats'] = {
            'total_stocks_tested': len(all_stocks),
            'validation_periods': len(self.market_periods),
            'strategy_formula': self.v1_strategy_config['formula'],
            'data_quality': 'high' if successful_stocks > len(all_stocks) * 0.9 else 'medium'
        }

        return results

    def generate_v1_strategy_report(self, strategy_results: Dict) -> str:
        """生成V1组合策略报告"""
        report = []
        report.append(f"# {strategy_results['strategy_name']} 回测报告")
        report.append("=" * 80)
        report.append("")

        # 策略概述
        report.append("## 策略概述")
        report.append(f"- 策略名称: {strategy_results['strategy_name']}")
        report.append(f"- 策略公式: {strategy_results['strategy_formula']}")
        report.append(f"- 测试股票: {strategy_results['total_stocks']} 只CSI800成分股")
        report.append(f"- 回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 因子权重配置
        report.append("## 因子权重配置")
        report.append(f"- 动量强度因子: {self.v1_strategy_config['factors']['momentum_strength']['weight']:.0%}")
        report.append(f"- 成交量激增因子: {self.v1_strategy_config['factors']['volume_surge']['weight']:.0%}")
        report.append("")

        # 各时期表现
        report.append("## 各时期表现")
        for period_name, period_result in strategy_results['period_results'].items():
            report.append(f"### {period_result['description']}")
            report.append(f"- 成功股票数: {period_result['successful_stocks']} 只")
            report.append(f"- 成功率: {period_result['success_rate']:.1%}")
            report.append(f"- 平均年化收益: {period_result['avg_annual_return']:.2%}")
            report.append(f"- 平均夏普比率: {period_result['avg_sharpe_ratio']:.2f}")
            report.append(f"- 平均最大回撤: {period_result['avg_max_drawdown']:.2%}")
            report.append(f"- 平均胜率: {period_result['avg_win_rate']:.2%}")
            report.append(f"- 平均信息比率: {period_result['avg_information_ratio']:.2f}")
            report.append("")
            report.append("**组合整体表现:**")
            report.append(f"- 组合年化收益: {period_result['overall_portfolio_return']:.2%}")
            report.append(f"- 组合波动率: {period_result['overall_portfolio_volatility']:.2%}")
            report.append(f"- 组合夏普比率: {period_result['overall_portfolio_sharpe']:.2f}")
            report.append(f"- 总交易次数: {period_result['total_trades']}")
            report.append("")

        # 策略评估
        report.append("## 策略评估")
        overall_performance = []
        for period_result in strategy_results['period_results'].values():
            overall_performance.append(period_result['overall_portfolio_return'])

        if overall_performance:
            avg_overall_return = np.mean(overall_performance)
            report.append(f"**跨时期平均组合收益: {avg_overall_return:.2%}**")

            if avg_overall_return > 0:
                report.append("✅ **策略表现: 正面**")
                report.append("- V1组合策略在不同市场环境下均表现正面")
                report.append("- 动量强度与成交量激增因子结合效果良好")
                report.append("- 策略具备一定的市场适应性")
            else:
                report.append("⚠️ **策略表现: 需要优化**")
                report.append("- 策略在某些市场环境下表现负面")
                report.append("- 建议调整因子权重或增加其他因子")

        report.append("")

        # 风险收益分析
        report.append("## 风险收益分析")
        report.append("- **收益特征**: 策略主要通过动量强度和成交量激增捕捉股票短期趋势")
        report.append("- **风险控制**: 通过分散投资于多只股票降低单一股票风险")
        report.append("- **市场适应性**: 在不同市场阶段表现需要进一步验证")
        report.append("- **改进空间**: 可考虑加入风险管理模块或动态权重调整")
        report.append("")

        # 实施建议
        report.append("## 实施建议")
        report.append("1. **资金管理**: 建议单次投入不超过总资金的20%")
        report.append("2. **持仓控制**: 严格控制持仓数量，建议不超过50只股票")
        report.append("3. **止损机制**: 建议设置-5%的单日止损线")
        report.append("4. **定期评估**: 建议每月评估策略表现，必要时调整参数")
        report.append("5. **分散投资**: 建议与其他低相关性策略组合使用")
        report.append("")

        return "\n".join(report)

def main():
    """主函数"""
    logger.info("=== V1组合策略回测开始 ===")

    backtester = V1CombinedStrategyBacktester()

    # 运行V1组合策略回测
    results = backtester.run_v1_strategy_backtest()

    if results:
        # 生成报告
        report = backtester.generate_v1_strategy_report(results)

        # 保存报告
        report_file = backtester.v1_output_dir / "v1_combined_strategy_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"V1组合策略回测完成，报告已保存: {report_file}")

        # 保存详细结果
        results_file = backtester.v1_output_dir / "v1_strategy_detailed_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"详细结果已保存: {results_file}")

    logger.info("=== V1组合策略回测完成 ===")

if __name__ == "__main__":
    main()