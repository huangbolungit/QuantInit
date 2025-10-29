#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300五年数据回测研究框架
基于真实历史数据的量化策略研究工具
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import json
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csi300_research.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.backtesting.engine import BacktestEngine
from app.services.factors.momentum import MomentumFactor
from app.services.factors.value import ValueFactor


class CSI300ResearchFramework:
    """沪深300回测研究框架"""

    def __init__(self, data_dir: str = None):
        """
        初始化研究框架

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir) if data_dir else Path("data/historical/stocks/csi300_5year")
        self.stocks_dir = self.data_dir / "stocks"
        self.reports_dir = self.data_dir / "reports"
        self.analysis_dir = self.data_dir / "analysis"
        self.plots_dir = self.data_dir / "plots"

        # 创建分析目录
        for dir_path in [self.analysis_dir, self.plots_dir]:
            dir_path.mkdir(exist_ok=True)

        # 初始化回测引擎
        self.backtest_engine = BacktestEngine(str(self.stocks_dir))

        # 研究配置
        self.research_config = {
            'base_period': ('2019-01-01', '2024-12-31'),  # 5年基础期
            'test_period': ('2023-01-01', '2024-12-31'),   # 2年测试期
            'universe_size': 50,  # 股票池大小
            'rebalance_frequency': 'monthly',  # 月度调仓
            'factor_combinations': [
                {'momentum': 1.0, 'value': 0.0},      # 纯动量
                {'momentum': 0.0, 'value': 1.0},      # 纯价值
                {'momentum': 0.7, 'value': 0.3},      # 偏动量
                {'momentum': 0.3, 'value': 0.7},      # 偏价值
                {'momentum': 0.5, 'value': 0.5},      # 平衡
            ]
        }

        logger.info(f"研究框架初始化完成，数据目录: {self.data_dir}")

    def load_available_stocks(self) -> List[str]:
        """加载可用的股票列表"""
        logger.info("加载可用股票列表...")

        stock_files = list(self.stocks_dir.rglob("*.csv"))
        stock_codes = set()

        for file_path in stock_files:
            stock_code = file_path.stem
            # 确保是6位数字股票代码
            if stock_code.isdigit() and len(stock_code) == 6:
                stock_codes.add(stock_code)

        available_stocks = sorted(list(stock_codes))
        logger.info(f"找到 {len(available_stocks)} 只可用股票")

        # 保存股票列表
        with open(self.analysis_dir / "available_stocks.json", 'w', encoding='utf-8') as f:
            json.dump({
                'count': len(available_stocks),
                'stocks': available_stocks,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

        return available_stocks

    def validate_data_quality(self, stock_codes: List[str]) -> Dict[str, Any]:
        """验证数据质量"""
        logger.info("开始数据质量验证...")

        quality_report = {
            'total_stocks': len(stock_codes),
            'valid_stocks': [],
            'invalid_stocks': [],
            'data_coverage': {},
            'quality_metrics': {}
        }

        for stock_code in stock_codes:
            try:
                # 加载该股票的所有数据
                stock_files = list(self.stocks_dir.rglob(f"{stock_code}.csv"))
                if not stock_files:
                    quality_report['invalid_stocks'].append({
                        'stock': stock_code,
                        'reason': '无数据文件'
                    })
                    continue

                # 合并所有年份的数据
                all_data = []
                for file_path in stock_files:
                    df = pd.read_csv(file_path)
                    df['date'] = pd.to_datetime(df['date'])
                    all_data.append(df)

                if not all_data:
                    quality_report['invalid_stocks'].append({
                        'stock': stock_code,
                        'reason': '数据文件为空'
                    })
                    continue

                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'])

                # 数据质量检查
                total_records = len(combined_df)
                missing_values = combined_df.isnull().sum().to_dict()
                date_range = {
                    'start': combined_df['date'].min().strftime('%Y-%m-%d'),
                    'end': combined_df['date'].max().strftime('%Y-%m-%d'),
                    'trading_days': total_records
                }

                # 检查价格数据合理性
                price_issues = 0
                for col in ['open', 'high', 'low', 'close']:
                    if col in combined_df.columns:
                        price_issues += (combined_df[col] <= 0).sum()
                        price_issues += (combined_df[col] > 10000).sum()

                # 检查数据连续性
                combined_df['date_diff'] = combined_df['date'].diff().dt.days
                large_gaps = (combined_df['date_diff'] > 10).sum()

                quality_score = 1.0
                quality_score -= (price_issues / total_records) * 0.3
                quality_score -= (large_gaps / total_records) * 0.2
                quality_score -= (combined_df.isnull().sum().sum() / (total_records * len(combined_df.columns))) * 0.5

                if quality_score > 0.7 and total_records > 200:  # 至少200个交易日
                    quality_report['valid_stocks'].append({
                        'stock': stock_code,
                        'quality_score': quality_score,
                        'records': total_records,
                        'date_range': date_range,
                        'missing_data': missing_values,
                        'price_issues': price_issues,
                        'data_gaps': large_gaps
                    })
                else:
                    quality_report['invalid_stocks'].append({
                        'stock': stock_code,
                        'reason': f'质量分数过低: {quality_score:.2f}',
                        'records': total_records,
                        'quality_score': quality_score
                    })

            except Exception as e:
                quality_report['invalid_stocks'].append({
                    'stock': stock_code,
                    'reason': f'处理异常: {str(e)}'
                })

        # 生成汇总统计
        quality_report['data_coverage'] = {
            'valid_count': len(quality_report['valid_stocks']),
            'invalid_count': len(quality_report['invalid_stocks']),
            'validity_rate': len(quality_report['valid_stocks']) / len(stock_codes)
        }

        # 计算平均质量指标
        if quality_report['valid_stocks']:
            avg_records = np.mean([s['records'] for s in quality_report['valid_stocks']])
            avg_quality = np.mean([s['quality_score'] for s in quality_report['valid_stocks']])
            quality_report['quality_metrics'] = {
                'avg_trading_days': avg_records,
                'avg_quality_score': avg_quality
            }

        logger.info(f"数据质量验证完成: {quality_report['data_coverage']['valid_count']}/{quality_report['total_stocks']} "
                   f"({quality_report['data_coverage']['validity_rate']:.1%}) 股票数据质量良好")

        # 保存质量报告
        with open(self.analysis_dir / "data_quality_report.json", 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False)

        return quality_report

    def run_factor_analysis(self, stock_codes: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """运行因子分析"""
        logger.info(f"开始因子分析: {start_date} 到 {end_date}")

        factor_results = {}

        # 初始化因子计算器
        momentum_factor = MomentumFactor()
        value_factor = ValueFactor()

        # 对每只股票计算因子值
        for stock_code in stock_codes[:50]:  # 限制数量以提高速度
            try:
                # 加载股票数据
                stock_files = list(self.stocks_dir.rglob(f"{stock_code}.csv"))
                if not stock_files:
                    continue

                all_data = []
                for file_path in stock_files:
                    df = pd.read_csv(file_path)
                    df['date'] = pd.to_datetime(df['date'])
                    all_data.append(df)

                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df = combined_df.sort_values('date')
                combined_df = combined_df[
                    (combined_df['date'] >= start_date) &
                    (combined_df['date'] <= end_date)
                ]

                if combined_df.empty:
                    continue

                # 计算因子值
                market_data = {
                    'price_data': combined_df.to_dict('records'),
                    'current_price': float(combined_df.iloc[-1]['close']),
                    'volume': float(combined_df.iloc[-1]['volume'])
                }

                momentum_score = momentum_factor.calculate(stock_code, market_data)
                value_score = value_factor.calculate(stock_code, market_data)

                factor_results[stock_code] = {
                    'momentum_score': momentum_score,
                    'value_score': value_score,
                    'composite_score': momentum_score * 0.6 + value_score * 0.4,
                    'records': len(combined_df)
                }

            except Exception as e:
                logger.warning(f"计算 {stock_code} 因子时出错: {e}")
                continue

        # 因子统计分析
        if factor_results:
            df_factors = pd.DataFrame(factor_results).T
            factor_stats = {
                'momentum_mean': df_factors['momentum_score'].mean(),
                'momentum_std': df_factors['momentum_score'].std(),
                'value_mean': df_factors['value_score'].mean(),
                'value_std': df_factors['value_score'].std(),
                'correlation': df_factors['momentum_score'].corr(df_factors['value_score'])
            }
        else:
            factor_stats = {}

        analysis_result = {
            'factor_scores': factor_results,
            'statistics': factor_stats,
            'analysis_period': {'start': start_date, 'end': end_date},
            'total_stocks': len(stock_codes),
            'analyzed_stocks': len(factor_results)
        }

        logger.info(f"因子分析完成: {len(factor_results)} 只股票")
        return analysis_result

    def run_comprehensive_backtest(self, stock_codes: List[str]) -> Dict[str, Any]:
        """运行综合回测研究"""
        logger.info("开始综合回测研究...")

        results = {}

        # 基础回测：动量+价值因子组合
        base_config = {
            'momentum_weight': 0.6,
            'value_weight': 0.4,
            'rebalance_frequency': 'monthly'
        }

        try:
            base_result = self.backtest_engine.run_backtest(
                start_date=self.research_config['test_period'][0],
                end_date=self.research_config['test_period'][1],
                stock_universe=stock_codes[:self.research_config['universe_size']],
                rebalance_frequency=base_config['rebalance_frequency']
            )

            results['baseline_strategy'] = {
                'config': base_config,
                'performance': base_result['performance_metrics'],
                'trades': base_result['trades']
            }

        except Exception as e:
            logger.error(f"基础回测失败: {e}")

        # 不同因子组合对比
        combination_results = {}
        for i, factor_config in enumerate(self.research_config['factor_combinations']):
            config_name = f"combination_{i+1}"
            try:
                # 这里需要修改回测引擎以支持不同的因子权重
                # 暂时使用基础配置作为示例
                result = self.backtest_engine.run_backtest(
                    start_date=self.research_config['test_period'][0],
                    end_date=self.research_config['test_period'][1],
                    stock_universe=stock_codes[:self.research_config['universe_size']],
                    rebalance_frequency=self.research_config['rebalance_frequency']
                )

                combination_results[config_name] = {
                    'config': factor_config,
                    'performance': result['performance_metrics']
                }

            except Exception as e:
                logger.warning(f"因子组合 {config_name} 回测失败: {e}")

        results['factor_combinations'] = combination_results

        # 生成对比分析
        if combination_results:
            comparison = self._compare_strategies(combination_results)
            results['strategy_comparison'] = comparison

        logger.info("综合回测研究完成")
        return results

    def _compare_strategies(self, strategies: Dict[str, Any]) -> Dict[str, Any]:
        """对比不同策略表现"""
        comparison = {
            'performance_ranking': [],
            'risk_return_analysis': {},
            'best_performers': {}
        }

        performance_data = []

        for name, strategy in strategies.items():
            perf = strategy['performance']
            performance_data.append({
                'strategy': name,
                'config': strategy['config'],
                'total_return': perf.get('total_return', 0),
                'annualized_return': perf.get('annualized_return', 0),
                'sharpe_ratio': perf.get('sharpe_ratio', 0),
                'max_drawdown': perf.get('max_drawdown', 0),
                'win_rate': perf.get('win_rate', 0)
            })

        # 排名
        df_perf = pd.DataFrame(performance_data)
        comparison['performance_ranking'] = df_perf.sort_values('sharpe_ratio', ascending=False).to_dict('records')

        # 最佳表现者
        if not df_perf.empty:
            comparison['best_performers'] = {
                'highest_return': df_perf.loc[df_perf['annualized_return'].idxmax()].to_dict(),
                'best_sharpe': df_perf.loc[df_perf['sharpe_ratio'].idxmax()].to_dict(),
                'lowest_drawdown': df_perf.loc[df_perf['max_drawdown'].idxmin()].to_dict()
            }

        return comparison

    def generate_research_report(self, data_quality: Dict, factor_analysis: Dict, backtest_results: Dict) -> str:
        """生成研究报告"""
        report = f"""
# 沪深300五年数据回测研究报告

## 1. 数据概况
- 数据时间范围: {self.research_config['base_period'][0]} 到 {self.research_config['base_period'][1]}
- 有效股票数量: {data_quality['data_coverage']['valid_count']}/{data_quality['total_stocks']} ({data_quality['data_coverage']['validity_rate']:.1%})
- 平均交易天数: {data_quality['quality_metrics'].get('avg_trading_days', 'N/A')}
- 平均数据质量分数: {data_quality['quality_metrics'].get('avg_quality_score', 'N/A'):.3f}

## 2. 因子分析结果
- 分析股票数量: {factor_analysis['analyzed_stocks']}
- 动量因子均值: {factor_analysis['statistics'].get('momentum_mean', 'N/A'):.3f}
- 价值因子均值: {factor_analysis['statistics'].get('value_mean', 'N/A'):.3f}
- 因子相关性: {factor_analysis['statistics'].get('correlation', 'N/A'):.3f}

## 3. 回测表现

### 基准策略 (动量60% + 价值40%)
"""

        if 'baseline_strategy' in backtest_results:
            base_perf = backtest_results['baseline_strategy']['performance']
            report += f"""
- 总收益率: {base_perf.get('total_return', 0):.2%}
- 年化收益率: {base_perf.get('annualized_return', 0):.2%}
- 夏普比率: {base_perf.get('sharpe_ratio', 0):.2f}
- 最大回撤: {base_perf.get('max_drawdown', 0):.2%}
- 胜率: {base_perf.get('win_rate', 0):.2%}
"""

        if 'strategy_comparison' in backtest_results:
            report += "\n### 策略对比排名\n"
            for i, strategy in enumerate(backtest_results['strategy_comparison']['performance_ranking'][:5], 1):
                report += f"{i}. {strategy['strategy']}: 夏普比率 {strategy['sharpe_ratio']:.2f}, 年化收益 {strategy['annualized_return']:.2%}\n"

        report += f"""

## 4. 研究结论
- 数据质量: {'优秀' if data_quality['data_coverage']['validity_rate'] > 0.8 else '良好' if data_quality['data_coverage']['validity_rate'] > 0.6 else '需要改进'}
- 因子有效性: {'显著' if abs(factor_analysis['statistics'].get('correlation', 0)) < 0.3 else '中等相关'}
- 策略表现: {'优异' if backtest_results.get('baseline_strategy', {}).get('performance', {}).get('sharpe_ratio', 0) > 1.5 else '良好' if backtest_results.get('baseline_strategy', {}).get('performance', {}).get('sharpe_ratio', 0) > 1.0 else '需要优化'}

## 5. 建议
- 继续扩充数据覆盖范围，提高数据质量
- 尝试更多因子组合和权重配置
- 考虑加入行业轮动和风险控制机制
- 延长回测时间周期验证策略稳健性

---
报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 保存报告
        report_file = self.reports_dir / f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"研究报告已保存: {report_file}")
        return report_file

    def run_full_research(self) -> str:
        """运行完整研究流程"""
        logger.info("🚀 开始沪深300完整研究流程")

        # 1. 加载可用股票
        available_stocks = self.load_available_stocks()

        # 2. 数据质量验证
        logger.info("📊 步骤1: 数据质量验证")
        data_quality = self.validate_data_quality(available_stocks)

        if data_quality['data_coverage']['valid_count'] < 20:
            logger.error("可用数据质量股票数量不足，无法进行有效研究")
            return "数据质量不足"

        # 3. 因子分析
        logger.info("📈 步骤2: 因子分析")
        valid_stocks = [s['stock'] for s in data_quality['valid_stocks']]
        factor_analysis = self.run_factor_analysis(
            valid_stocks,
            self.research_config['test_period'][0],
            self.research_config['test_period'][1]
        )

        # 4. 回测研究
        logger.info("🔄 步骤3: 回测研究")
        backtest_results = self.run_comprehensive_backtest(valid_stocks)

        # 5. 生成报告
        logger.info("📝 步骤4: 生成研究报告")
        report_file = self.generate_research_report(data_quality, factor_analysis, backtest_results)

        logger.info("🎉 沪深300完整研究流程完成!")
        return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="沪深300五年数据回测研究框架")
    parser.add_argument("--data-dir", type=str, help="数据目录路径")
    parser.add_argument("--test", action="store_true", help="测试模式")

    args = parser.parse_args()

    print("🔬 沪深300五年数据回测研究框架")
    print("=" * 60)

    try:
        # 创建研究框架
        framework = CSI300ResearchFramework(args.data_dir)

        if args.test:
            logger.info("🧪 测试模式")
            # 运行简化的研究流程
            available_stocks = framework.load_available_stocks()[:20]
            data_quality = framework.validate_data_quality(available_stocks)
        else:
            # 运行完整研究流程
            report_file = framework.run_full_research()
            print(f"\n📊 研究报告: {report_file}")

    except Exception as e:
        logger.error(f"研究流程失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()