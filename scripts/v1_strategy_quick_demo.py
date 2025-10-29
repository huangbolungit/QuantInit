#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V1组合策略快速演示 - 生成完整量化指标报告
使用少量股票演示完整的性能指标计算
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.full_sample_factor_validator import FullSampleFactorValidator

class V1StrategyQuickDemo(FullSampleFactorValidator):
    """V1组合策略快速演示"""

    def __init__(self):
        super().__init__()

        # 策略配置
        self.v1_strategy_config = {
            'name': 'V1组合策略-演示版',
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
            }
        }

        # 输出目录
        self.output_dir = Path("v1_strategy_demo_results")
        self.output_dir.mkdir(exist_ok=True)

    def calculate_combined_factor_scores(self, data: pd.DataFrame):
        """计算组合因子得分"""
        if data.empty or len(data) < 20:
            return None, None

        try:
            # 计算收益率
            returns = data['close'].pct_change().dropna()

            # 计算动量强度因子 (LWR)
            lwr_period = 14
            high = data['high'].rolling(lwr_period).max()
            low = data['low'].rolling(lwr_period).min()
            close = data['close']

            denominator = high - low
            denominator = denominator.replace(0, np.nan)
            lwr = -100 * (high - close) / denominator
            momentum_scores = lwr.fillna(-50.0)

            # 计算成交量激增因子
            volume_ma20 = data['volume'].rolling(window=20).mean()
            volume_ma20 = volume_ma20.replace(0, np.nan)
            volume_ratio = data['volume'] / volume_ma20
            volume_scores = volume_ratio.fillna(1.0)

            # 标准化因子得分
            momentum_normalized = self._normalize_scores(momentum_scores)
            volume_normalized = self._normalize_scores(volume_scores)

            # 计算组合得分
            momentum_weight = self.v1_strategy_config['factors']['momentum_strength']['weight']
            volume_weight = self.v1_strategy_config['factors']['volume_surge']['weight']

            combined_scores = (momentum_normalized * momentum_weight) + (volume_normalized * volume_weight)

            return combined_scores, returns

        except Exception as e:
            print(f"计算组合因子得分失败: {e}")
            return None, None

    def _normalize_scores(self, scores: pd.Series) -> pd.Series:
        """标准化因子得分到0-1范围"""
        if scores.empty:
            return scores

        try:
            # 滚动标准化
            rolling_mean = scores.rolling(window=252, min_periods=60).mean()
            rolling_std = scores.rolling(window=252, min_periods=60).std()
            rolling_std = rolling_std.replace(0, 1e-8)

            normalized = (scores - rolling_mean) / rolling_std

            # 映射到0-1范围
            min_val = normalized.min()
            max_val = normalized.max()

            if max_val > min_val:
                final_normalized = (normalized - min_val) / (max_val - min_val)
            else:
                final_normalized = pd.Series(0.5, index=normalized.index)

            return final_normalized.fillna(0.5)

        except Exception as e:
            print(f"标准化失败: {e}")
            return pd.Series(0.5, index=scores.index)

    def calculate_strategy_performance(self, combined_scores: pd.Series, returns: pd.Series):
        """计算策略表现"""
        if combined_scores.empty or returns.empty:
            return {}

        try:
            # 对齐数据
            aligned_data = pd.concat([combined_scores, returns], axis=1).dropna()
            if len(aligned_data) < 10:
                return {}

            aligned_scores = aligned_data.iloc[:, 0]
            aligned_returns = aligned_data.iloc[:, 1]

            # 买入信号：组合得分最高的20%
            factor_quantile = aligned_scores.rank(pct=True)
            buy_signal = factor_quantile > 0.8
            strategy_returns = aligned_returns[buy_signal]

            if len(strategy_returns) == 0:
                return {}

            # 计算关键指标
            total_return = (1 + strategy_returns).prod() - 1
            trading_days = len(strategy_returns)
            annual_return = (1 + total_return) ** (252 / trading_days) - 1

            # 夏普比率
            excess_returns = strategy_returns - 0.03/252
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0

            # 最大回撤
            cumulative = (1 + strategy_returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()

            # 胜率
            win_rate = (strategy_returns > 0).mean()

            # 信息比率
            market_returns = aligned_returns
            excess_returns_strategy = strategy_returns - market_returns.reindex(strategy_returns.index, fill_value=0)
            information_ratio = excess_returns_strategy.mean() / excess_returns_strategy.std() * np.sqrt(252) if excess_returns_strategy.std() > 0 else 0

            return {
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'information_ratio': information_ratio,
                'total_trades': len(strategy_returns),
                'trading_days': trading_days,
                'selection_rate': len(strategy_returns) / len(aligned_returns)
            }

        except Exception as e:
            print(f"计算策略表现失败: {e}")
            return {}

    def run_quick_demo(self):
        """运行快速演示"""
        print("=== V1组合策略快速演示 ===")

        # 选择有代表性的股票样本
        sample_stocks = [
            "000001",  # 平安银行
            "000002",  # 万科A
            "600000",  # 浦发银行
            "600036",  # 招商银行
            "600519",  # 贵州茅台
            "000858",  # 五粮液
            "600031",  # 三一重工
            "000063",  # 中兴通讯
            "002415",  # 海康威视
            "300059"   # 东方财富
        ]

        results = {
            'strategy_name': self.v1_strategy_config['name'],
            'strategy_formula': self.v1_strategy_config['formula'],
            'sample_stocks': len(sample_stocks),
            'period_results': {},
            'individual_stock_results': {},
            'validation_stats': {}
        }

        # 按时期测试
        for period_name, period_config in self.market_periods.items():
            print(f"\n--- 测试时期: {period_name} ({period_config['description']}) ---")

            period_performance_metrics = []
            successful_stocks = 0

            for stock_code in sample_stocks:
                print(f"处理股票: {stock_code}")

                # 加载数据
                data = self.load_stock_data(
                    stock_code,
                    period_config['start_date'],
                    period_config['end_date']
                )

                if data.empty or len(data) < 20:
                    print(f"  数据不足，跳过")
                    continue

                # 计算组合因子得分
                combined_scores, returns = self.calculate_combined_factor_scores(data)

                if combined_scores is None or returns is None:
                    print(f"  因子计算失败，跳过")
                    continue

                # 计算策略表现
                strategy_metrics = self.calculate_strategy_performance(combined_scores, returns)

                if strategy_metrics:
                    strategy_metrics['stock_code'] = stock_code
                    period_performance_metrics.append(strategy_metrics)
                    results['individual_stock_results'][f"{stock_code}_{period_name}"] = strategy_metrics
                    successful_stocks += 1

                    print(f"  年化收益: {strategy_metrics['annual_return']:.2%}")
                    print(f"  夏普比率: {strategy_metrics['sharpe_ratio']:.2f}")
                    print(f"  最大回撤: {strategy_metrics['max_drawdown']:.2%}")
                    print(f"  胜率: {strategy_metrics['win_rate']:.2%}")
                else:
                    print(f"  策略计算失败")

            # 汇总时期结果
            if period_performance_metrics:
                period_df = pd.DataFrame(period_performance_metrics)

                # 计算平均表现
                avg_annual_return = period_df['annual_return'].mean()
                avg_sharpe_ratio = period_df['sharpe_ratio'].mean()
                avg_max_drawdown = period_df['max_drawdown'].mean()
                avg_win_rate = period_df['win_rate'].mean()
                avg_information_ratio = period_df['information_ratio'].mean()

                # 计算标准差
                std_annual_return = period_df['annual_return'].std()
                std_sharpe_ratio = period_df['sharpe_ratio'].std()

                results['period_results'][period_name] = {
                    'description': period_config['description'],
                    'successful_stocks': successful_stocks,
                    'total_stocks': len(sample_stocks),
                    'success_rate': successful_stocks / len(sample_stocks),
                    'avg_annual_return': avg_annual_return,
                    'std_annual_return': std_annual_return,
                    'avg_sharpe_ratio': avg_sharpe_ratio,
                    'std_sharpe_ratio': std_sharpe_ratio,
                    'avg_max_drawdown': avg_max_drawdown,
                    'avg_win_rate': avg_win_rate,
                    'avg_information_ratio': avg_information_ratio,
                    'total_trades': period_df['total_trades'].sum()
                }

                print(f"\n{period_name} 汇总结果:")
                print(f"  成功股票: {successful_stocks}/{len(sample_stocks)}")
                print(f"  平均年化收益: {avg_annual_return:.2%} (±{std_annual_return:.2%})")
                print(f"  平均夏普比率: {avg_sharpe_ratio:.2f} (±{std_sharpe_ratio:.2f})")
                print(f"  平均最大回撤: {avg_max_drawdown:.2%}")
                print(f"  平均胜率: {avg_win_rate:.2%}")

        # 验证统计
        results['validation_stats'] = {
            'total_stocks_tested': len(sample_stocks),
            'validation_periods': len(self.market_periods),
            'strategy_formula': self.v1_strategy_config['formula'],
            'data_quality': 'demo'
        }

        return results

    def generate_demo_report(self, results: dict) -> str:
        """生成演示报告"""
        report = []
        report.append(f"# {results['strategy_name']} 演示报告")
        report.append("=" * 80)
        report.append("")

        # 策略概述
        report.append("## 策略概述")
        report.append(f"- 策略名称: {results['strategy_name']}")
        report.append(f"- 策略公式: {results['strategy_formula']}")
        report.append(f"- 测试股票: {results['sample_stocks']} 只代表性股票")
        report.append(f"- 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 关键量化指标汇总
        report.append("## 📊 关键量化指标汇总")
        for period_name, period_result in results['period_results'].items():
            report.append(f"### {period_result['description']}")
            report.append(f"- 成功股票数: {period_result['successful_stocks']}/{period_result['total_stocks']}")
            report.append(f"- 成功率: {period_result['success_rate']:.1%}")
            report.append("")

            report.append("**📈 收益指标**:")
            report.append(f"- 平均年化收益率: {period_result['avg_annual_return']:.2%} (±{period_result['std_annual_return']:.2%})")
            report.append(f"- 超额收益稳定性: {'高' if period_result['std_annual_return'] < 0.2 else '中' if period_result['std_annual_return'] < 0.5 else '低'}")
            report.append("")

            report.append("**🎯 风险指标**:")
            report.append(f"- 平均夏普比率: {period_result['avg_sharpe_ratio']:.2f} (±{period_result['std_sharpe_ratio']:.2f})")
            report.append(f"- 夏普比率评级: {'优秀' if period_result['avg_sharpe_ratio'] > 2 else '良好' if period_result['avg_sharpe_ratio'] > 1 else '一般' if period_result['avg_sharpe_ratio'] > 0 else '较差'}")
            report.append(f"- 平均最大回撤: {period_result['avg_max_drawdown']:.2%}")
            report.append(f"- 回撤控制: {'优秀' if period_result['avg_max_drawdown'] > -0.1 else '良好' if period_result['avg_max_drawdown'] > -0.2 else '需要改进'}")
            report.append("")

            report.append("**🎲 交易指标**:")
            report.append(f"- 平均胜率: {period_result['avg_win_rate']:.2%}")
            report.append(f"- 胜率评级: {'优秀' if period_result['avg_win_rate'] > 0.6 else '良好' if period_result['avg_win_rate'] > 0.5 else '一般'}")
            report.append(f"- 平均信息比率: {period_result['avg_information_ratio']:.2f}")
            report.append(f"- 总交易次数: {period_result['total_trades']}")
            report.append("")

        # 个股表现展示
        report.append("## 🏆 个股表现展示")
        report.append("### 各股票详细表现")

        for period_name in results['period_results'].keys():
            report.append(f"#### {results['period_results'][period_name]['description']}")

            period_stocks = {k: v for k, v in results['individual_stock_results'].items() if k.endswith(period_name)}

            # 按年化收益排序
            sorted_stocks = sorted(period_stocks.items(), key=lambda x: x[1]['annual_return'], reverse=True)

            report.append("| 股票代码 | 年化收益 | 夏普比率 | 最大回撤 | 胜率 |")
            report.append("|---------|---------|---------|---------|------|")

            for stock_key, metrics in sorted_stocks:
                stock_code = stock_key.split('_')[0]
                report.append(f"| {stock_code} | {metrics['annual_return']:.2%} | {metrics['sharpe_ratio']:.2f} | {metrics['max_drawdown']:.2%} | {metrics['win_rate']:.2%} |")

            report.append("")

        # 策略评估
        report.append("## 🎯 策略评估")

        # 计算跨时期表现
        all_returns = [r['avg_annual_return'] for r in results['period_results'].values()]
        all_sharpes = [r['avg_sharpe_ratio'] for r in results['period_results'].values()]

        avg_return = np.mean(all_returns)
        avg_sharpe = np.mean(all_sharpes)

        report.append(f"**跨时期平均表现**:")
        report.append(f"- 平均年化收益: {avg_return:.2%}")
        report.append(f"- 平均夏普比率: {avg_sharpe:.2f}")
        report.append("")

        if avg_return > 0.1 and avg_sharpe > 1:
            report.append("✅ **策略评级: 优秀**")
            report.append("- V1组合策略在不同市场环境下均表现优异")
            report.append("- 动量强度与成交量激增因子结合效果显著")
            report.append("- 策略具备良好的市场适应性和风险控制能力")
        elif avg_return > 0 and avg_sharpe > 0.5:
            report.append("✅ **策略评级: 良好**")
            report.append("- V1组合策略表现正面，具备投资价值")
            report.append("- 建议进一步优化和扩大测试范围")
        else:
            report.append("⚠️ **策略评级: 需要优化**")
            report.append("- 策略表现有待提升，建议调整因子权重")
            report.append("- 可考虑增加其他因子或风险管理模块")

        report.append("")

        # 实施建议
        report.append("## 💡 实施建议")
        report.append("1. **资金管理**: 单次投入不超过总资金的20%")
        report.append("2. **持仓控制**: 严格控制在50只股票以内")
        report.append("3. **止损机制**: 设置-5%的单日止损线")
        report.append("4. **定期评估**: 每月评估策略表现，必要时调整参数")
        report.append("5. **分散投资**: 与其他低相关性策略组合使用")
        report.append("")

        # 风险提示
        report.append("## ⚠️ 风险提示")
        report.append("- 本报告基于历史数据回测，不代表未来表现")
        report.append("- 策略表现可能受市场环境变化影响")
        report.append("- 投资有风险，请谨慎决策")
        report.append("- 建议在充分理解策略原理后进行投资")
        report.append("")

        return "\n".join(report)

def main():
    """主函数"""
    demo = V1StrategyQuickDemo()

    print("开始运行V1组合策略快速演示...")
    results = demo.run_quick_demo()

    if results and results.get('period_results'):
        # 生成报告
        report = demo.generate_demo_report(results)

        # 保存报告
        report_file = demo.output_dir / "v1_strategy_demo_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n=== 演示完成 ===")
        print(f"报告已保存: {report_file}")

        # 保存详细结果
        results_file = demo.output_dir / "v1_strategy_demo_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"详细结果已保存: {results_file}")

        # 输出关键指标
        print(f"\n=== 关键指标摘要 ===")
        for period_name, period_result in results['period_results'].items():
            print(f"{period_name}:")
            print(f"  年化收益: {period_result['avg_annual_return']:.2%}")
            print(f"  夏普比率: {period_result['avg_sharpe_ratio']:.2f}")
            print(f"  最大回撤: {period_result['avg_max_drawdown']:.2%}")
            print(f"  胜率: {period_result['avg_win_rate']:.2%}")

    else:
        print("演示失败，没有生成有效结果")

if __name__ == "__main__":
    main()