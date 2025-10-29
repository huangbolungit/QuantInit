#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Strategy Comparison - 策略对比分析
对比均值回归和动量策略的表现
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class StrategyComparator:
    """策略对比分析器"""

    def __init__(self):
        self.results_dir = Path("optimization_results")
        self.comparison_results = {}

    def load_optimization_results(self, strategy_name: str) -> Dict[str, Any]:
        """加载优化结果"""
        # 查找最新的优化结果文件
        pattern = f"*{strategy_name}*"
        result_files = list(self.results_dir.glob(f"optimization_*{strategy_name}*.json"))

        if not result_files:
            logger.warning(f"未找到 {strategy_name} 的优化结果")
            return {}

        # 按修改时间排序，取最新的
        latest_file = max(result_files, key=lambda x: x.stat().st_mtime)

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            logger.info(f"加载 {strategy_name} 优化结果: {latest_file}")
            return results
        except Exception as e:
            logger.error(f"加载优化结果失败: {e}")
            return {}

    def compare_strategies(self, strategies: List[str]) -> Dict[str, Any]:
        """对比策略表现"""
        comparison = {
            'strategies': {},
            'best_performers': {},
            'comparison_metrics': {}
        }

        # 加载各策略结果
        for strategy in strategies:
            results = self.load_optimization_results(strategy)
            if results:
                comparison['strategies'][strategy] = results

        if len(comparison['strategies']) < 2:
            logger.warning("可对比的策略数量不足")
            return comparison

        # 提取关键指标进行对比
        metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'annual_return']

        for metric in metrics:
            comparison['comparison_metrics'][metric] = {}

            for strategy, results in comparison['strategies'].items():
                if 'best_result' in results and 'performance_metrics' in results['best_result']:
                    perf = results['best_result']['performance_metrics']
                    comparison['comparison_metrics'][metric][strategy] = perf.get(metric, 0)

        # 找出各指标的最佳策略
        for metric in metrics:
            metric_values = comparison['comparison_metrics'][metric]
            if metric_values:
                if metric == 'max_drawdown':
                    # 最大回撤越小越好
                    best_strategy = min(metric_values.keys(), key=lambda k: metric_values[k])
                else:
                    # 其他指标越大越好
                    best_strategy = max(metric_values.keys(), key=lambda k: metric_values[k])

                comparison['best_performers'][metric] = {
                    'strategy': best_strategy,
                    'value': metric_values[best_strategy]
                }

        return comparison

    def generate_comparison_report(self, comparison: Dict[str, Any]) -> str:
        """生成对比报告"""
        report = []
        report.append("# 策略性能对比报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 策略概览
        report.append("## 📊 策略概览")
        report.append("")
        for strategy, results in comparison['strategies'].items():
            if 'best_result' in results:
                perf = results['best_result']['performance_metrics']
                params = results['best_result']['parameters']

                report.append(f"### {strategy}")
                report.append(f"- **总收益率**: {perf.get('total_return', 0):.2%}")
                report.append(f"- **年化收益**: {perf.get('annual_return', 0):.2%}")
                report.append(f"- **夏普比率**: {perf.get('sharpe_ratio', 0):.2f}")
                report.append(f"- **最大回撤**: {perf.get('max_drawdown', 0):.2%}")
                report.append(f"- **最优参数**: {params}")
                report.append("")

        # 最佳表现者
        report.append("## 🏆 各指标最佳表现")
        report.append("")

        for metric, best in comparison['best_performers'].items():
            metric_name = {
                'total_return': '总收益率',
                'sharpe_ratio': '夏普比率',
                'max_drawdown': '最大回撤',
                'annual_return': '年化收益'
            }.get(metric, metric)

            if metric == 'max_drawdown':
                report.append(f"- **{metric_name}**: {best['strategy']} ({best['value']:.2%}) - 回撤最小")
            else:
                report.append(f"- **{metric_name}**: {best['strategy']} ({best['value']:.2%})")

        report.append("")

        # 详细对比表格
        report.append("## 📈 详细对比")
        report.append("")

        metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'annual_return']
        metric_names = ['总收益率', '夏普比率', '最大回撤', '年化收益']

        report.append("| 策略 | " + " | ".join(metric_names) + " |")
        report.append("|---" + "---|" * len(metric_names))

        for strategy in comparison['strategies'].keys():
            if strategy in comparison['comparison_metrics']:
                values = comparison['comparison_metrics'][strategy]
                row_values = []

                for metric in metrics:
                    value = values.get(metric, 0)
                    if metric == 'max_drawdown':
                        row_values.append(f"{value:.2%}")
                    else:
                        row_values.append(f"{value:.2%}")

                report.append(f"| {strategy} | " + " | ".join(row_values) + " |")

        report.append("")

        # 综合评分
        report.append("## 🎯 综合评分")
        report.append("")

        # 计算综合评分 (归一化后加权平均)
        scores = {}
        for strategy in comparison['strategies'].keys():
            if strategy in comparison['comparison_metrics']:
                values = comparison['comparison_metrics'][strategy']

                # 归一化评分 (0-100)
                total_score = 0

                # 总收益率 (权重30%)
                if 'total_return' in values:
                    total_score += min(max(values['total_return'] * 100, 0), 100) * 0.3

                # 夏普比率 (权重40%)
                if 'sharpe_ratio' in values:
                    total_score += min(max(values['sharpe_ratio'] * 20, 0), 100) * 0.4

                # 最大回撤 (权重30%，越小越好)
                if 'max_drawdown' in values:
                    # 将回撤转换为正向评分
                    drawdown_score = max(0, (1 - values['max_drawdown']) * 100)
                    total_score += drawdown_score * 0.3

                scores[strategy] = total_score

        # 按综合评分排序
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        report.append("| 排名 | 策略 | 综合评分 |")
        report.append("|---|---|---|")

        for i, (strategy, score) in enumerate(sorted_scores, 1):
            report.append(f"| {i} | {strategy} | {score:.1f} |")

        return "\n".join(report)

    def save_comparison_results(self, comparison: Dict[str, Any], filename: str = None):
        """保存对比结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategy_comparison_{timestamp}.json"

        output_path = self.results_dir / filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            logger.info(f"对比结果已保存: {output_path}")
        except Exception as e:
            logger.error(f"保存对比结果失败: {e}")

def main():
    """主函数"""
    comparator = StrategyComparator()

    # 对比均值回归和动量策略
    strategies = ['OptimizedMeanReversion', 'CompatibleMomentum']

    logger.info("开始策略对比分析...")
    comparison = comparator.compare_strategies(strategies)

    if comparison['strategies']:
        # 生成报告
        report = comparator.generate_comparison_report(comparison)

        # 保存报告
        report_file = Path("optimization_results") / f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print("=== 策略对比报告 ===")
        print(report)
        print(f"\n详细报告已保存至: {report_file}")

        # 保存对比数据
        comparator.save_comparison_results(comparison)
    else:
        print("未找到足够的策略结果进行对比")

if __name__ == "__main__":
    main()