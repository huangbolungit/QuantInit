#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最大化利用现有数据的策略验证工具
基于已下载的57只股票进行完整的量化策略研究
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maximize_current_data.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.backtesting.engine import BacktestEngine


class DataMaximizer:
    """数据最大化利用工具"""

    def __init__(self):
        self.data_dir = Path("data/historical/stocks/csi300_5year/stocks")
        self.results_dir = Path("data/strategy_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def load_available_stocks(self) -> Dict[str, pd.DataFrame]:
        """加载所有可用的股票数据"""
        available_stocks = {}

        logger.info("扫描可用股票数据...")

        # 遍历所有年份目录
        for year_dir in self.data_dir.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                year = int(year_dir.name)
                logger.info(f"处理 {year} 年数据...")

                # 加载该年份的所有股票
                for stock_file in year_dir.glob("*.csv"):
                    stock_code = stock_file.stem
                    try:
                        df = pd.read_csv(stock_file)
                        df['date'] = pd.to_datetime(df['date'])

                        if stock_code not in available_stocks:
                            available_stocks[stock_code] = []
                        available_stocks[stock_code].append(df)

                    except Exception as e:
                        logger.warning(f"读取 {stock_code} 数据失败: {e}")

        # 合并每只股票的所有年份数据
        consolidated_stocks = {}
        for stock_code, dataframes in available_stocks.items():
            if dataframes:
                combined_df = pd.concat(dataframes, ignore_index=True)
                combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'])
                consolidated_stocks[stock_code] = combined_df
                logger.info(f"股票 {stock_code}: {len(combined_df)} 条数据 ({combined_df['date'].min().date()} 到 {combined_df['date'].max().date()})")

        logger.info(f"总共加载了 {len(consolidated_stocks)} 只股票数据")
        return consolidated_stocks

    def analyze_data_coverage(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """分析数据覆盖情况"""
        coverage_info = {
            'total_stocks': len(stock_data),
            'date_ranges': {},
            'data_quality': {},
            'sector_distribution': {}
        }

        all_dates = set()
        for stock_code, df in stock_data.items():
            date_range = {
                'start': df['date'].min().date(),
                'end': df['date'].max().date(),
                'trading_days': len(df)
            }
            coverage_info['date_ranges'][stock_code] = date_range

            # 收集所有交易日期
            dates = set(df['date'].dt.date)
            all_dates.update(dates)

            # 数据质量检查
            missing_values = df.isnull().sum().sum()
            coverage_info['data_quality'][stock_code] = {
                'missing_values': missing_values,
                'completeness': 1 - (missing_values / (len(df) * len(df.columns)))
            }

        coverage_info['overall_date_range'] = {
            'start': min(all_dates),
            'end': max(all_dates),
            'total_trading_days': len(all_dates)
        }

        return coverage_info

    def generate_stock_universe_configs(self, stock_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """生成不同的股票池配置"""
        stock_codes = list(stock_data.keys())

        configs = []

        # 配置1: 全部可用股票
        configs.append({
            'name': '全部可用股票',
            'stocks': stock_codes,
            'count': len(stock_codes)
        })

        # 配置2: 前20只股票
        configs.append({
            'name': '前20只股票',
            'stocks': stock_codes[:20],
            'count': 20
        })

        # 配置3: 随机选择15只股票
        np.random.shuffle(stock_codes)
        configs.append({
            'name': '随机15只股票',
            'stocks': stock_codes[:15],
            'count': 15
        })

        # 配置4: 分行业选择 (如果有行业信息)
        # 这里简化为按股票代码选择

        return configs

    def run_comprehensive_backtests(self, stock_data: Dict[str, pd.DataFrame]):
        """运行全面的回测分析"""
        logger.info("开始全面回测分析...")

        # 生成股票池配置
        configs = self.generate_stock_universe_configs(stock_data)

        # 回测参数组合
        strategies = [
            {'momentum': 0.7, 'value': 0.3, 'name': '动量主导'},
            {'momentum': 0.5, 'value': 0.5, 'name': '均衡策略'},
            {'momentum': 0.3, 'value': 0.7, 'name': '价值主导'},
        ]

        rebalance_frequencies = ['weekly', 'monthly']

        all_results = []

        for config in configs:
            logger.info(f"测试股票池: {config['name']} ({config['count']}只股票)")

            for strategy in strategies:
                for frequency in rebalance_frequencies:
                    try:
                        # 创建回测引擎
                        engine = BacktestEngine(str(self.data_dir))
                        engine.initial_capital = 1000000
                        engine.set_factor_weights(strategy['momentum'], strategy['value'])

                        # 运行回测
                        start_date = '2021-01-01'
                        end_date = '2024-12-31'

                        logger.info(f"  策略: {strategy['name']}, 调仓频率: {frequency}")

                        results = engine.run_backtest(
                            start_date=start_date,
                            end_date=end_date,
                            stock_universe=config['stocks'],
                            rebalance_frequency=frequency
                        )

                        # 生成报告
                        report = engine.generate_report(results)

                        # 保存结果
                        result_summary = {
                            'stock_universe': config['name'],
                            'stock_count': config['count'],
                            'strategy': strategy['name'],
                            'momentum_weight': strategy['momentum'],
                            'value_weight': strategy['value'],
                            'rebalance_frequency': frequency,
                            'start_date': start_date,
                            'end_date': end_date,
                            'results': results,
                            'report': report,
                            'timestamp': datetime.now().isoformat()
                        }

                        all_results.append(result_summary)

                        # 打印关键指标
                        if 'performance_metrics' in results:
                            perf = results['performance_metrics']
                            logger.info(f"    总收益率: {perf.get('total_return', 0):.2%}")
                            logger.info(f"    年化收益率: {perf.get('annualized_return', 0):.2%}")
                            logger.info(f"    最大回撤: {perf.get('max_drawdown', 0):.2%}")
                            logger.info(f"    夏普比率: {perf.get('sharpe_ratio', 0):.2f}")

                    except Exception as e:
                        logger.error(f"回测失败: {e}")
                        continue

        # 保存所有结果
        results_file = self.results_dir / f"comprehensive_backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"回测结果已保存到: {results_file}")

        # 生成汇总报告
        self.generate_summary_report(all_results)

        return all_results

    def generate_summary_report(self, results: List[Dict[str, Any]]):
        """生成汇总报告"""
        logger.info("生成汇总报告...")

        report_lines = [
            "# 量化策略回测汇总报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"测试组合数量: {len(results)}",
            "",
            "## 策略表现汇总",
            "",
            "| 股票池 | 策略 | 调仓频率 | 总收益率 | 年化收益率 | 最大回撤 | 夏普比率 |",
            "|--------|------|----------|----------|------------|----------|----------|"
        ]

        best_strategy = None
        best_sharpe = -float('inf')

        for result in results:
            perf = result.get('results', {}).get('performance_metrics', {})

            total_return = perf.get('total_return', 0) * 100
            annual_return = perf.get('annualized_return', 0) * 100
            max_drawdown = perf.get('max_drawdown', 0) * 100
            sharpe_ratio = perf.get('sharpe_ratio', 0)

            line = f"| {result['stock_universe']} | {result['strategy']} | {result['rebalance_frequency']} | {total_return:.2f}% | {annual_return:.2f}% | {max_drawdown:.2f}% | {sharpe_ratio:.2f} |"
            report_lines.append(line)

            # 记录最佳策略
            if sharpe_ratio > best_sharpe:
                best_sharpe = sharpe_ratio
                best_strategy = result

        report_lines.extend([
            "",
            "## 最佳策略",
            f"策略: {best_strategy['strategy']}",
            f"股票池: {best_strategy['stock_universe']}",
            f"调仓频率: {best_strategy['rebalance_frequency']}",
            f"夏普比率: {best_sharpe:.2f}",
            "",
            "## 建议",
            "1. 基于现有57只股票数据，可以有效的进行量化策略研究和验证",
            "2. 建议优先使用夏普比率较高的策略组合",
            "3. 在网络条件改善后，可以扩展到更多股票进行验证",
            "",
            "---",
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])

        # 保存报告
        report_file = self.results_dir / f"strategy_summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"汇总报告已保存到: {report_file}")

        # 打印最佳策略信息
        logger.info("=" * 50)
        logger.info("最佳策略发现:")
        logger.info(f"策略: {best_strategy['strategy']}")
        logger.info(f"股票池: {best_strategy['stock_universe']}")
        logger.info(f"夏普比率: {best_sharpe:.2f}")
        logger.info("=" * 50)


def main():
    """主函数"""
    maximizer = DataMaximizer()

    # 加载可用数据
    logger.info("开始最大化利用现有数据...")
    stock_data = maximizer.load_available_stocks()

    if not stock_data:
        logger.error("没有找到可用的股票数据")
        return

    # 分析数据覆盖
    coverage = maximizer.analyze_data_coverage(stock_data)
    logger.info(f"数据覆盖分析: {coverage['total_stocks']} 只股票")
    logger.info(f"时间范围: {coverage['overall_date_range']['start']} 到 {coverage['overall_date_range']['end']}")

    # 运行全面回测
    results = maximizer.run_comprehensive_backtests(stock_data)

    logger.info(f"完成 {len(results)} 个策略组合的回测分析")


if __name__ == "__main__":
    main()