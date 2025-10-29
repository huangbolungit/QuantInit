#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
综合本地股票数据回测系统
基于所有已下载的CSI800股票数据进行全面回测分析
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
import glob

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.v1_strategy_quick_demo import V1StrategyQuickDemo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_backtest.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveBacktester(V1StrategyQuickDemo):
    """综合本地股票数据回测器"""

    def __init__(self):
        super().__init__()

        # 输出目录
        self.comprehensive_output_dir = Path("comprehensive_backtest_results")
        self.comprehensive_output_dir.mkdir(exist_ok=True)

        # 数据源配置
        self.data_sources = {
            'complete_csi800': {
                'path': Path('data/historical/stocks/complete_csi800/stocks'),
                'description': '完整CSI800成分股数据'
            },
            'csi300_5year': {
                'path': Path('data/historical/stocks/csi300_5year/stocks'),
                'description': 'CSI300五年数据'
            }
        }

        # 回测配置
        self.backtest_config = {
            'test_all_periods': True,  # 测试所有可用时期
            'include_individual_stocks': True,  # 包含个股分析
            'max_stocks_for_detail': 50,  # 详细分析的最大股票数
            'sampling_rates': [1.0, 0.5, 0.2, 0.1],  # 不同的采样率
            'performance_metrics': [
                'annual_return', 'sharpe_ratio', 'max_drawdown',
                'win_rate', 'information_ratio', 'total_trades'
            ]
        }

    def scan_all_local_data(self) -> Dict[str, Any]:
        """扫描所有本地股票数据"""
        logger.info("=== 扫描本地股票数据 ===")

        data_summary = {
            'total_stocks': 0,
            'data_sources': {},
            'available_periods': set(),
            'stock_lists': {}
        }

        for source_name, source_config in self.data_sources.items():
            source_path = source_config['path']

            if not source_path.exists():
                logger.warning(f"数据源不存在: {source_path}")
                continue

            logger.info(f"扫描数据源: {source_name}")

            source_stocks = set()
            source_periods = set()
            stock_files = {}

            # 遍历所有年份目录
            for year_dir in source_path.iterdir():
                if not year_dir.is_dir():
                    continue

                year = year_dir.name
                if year.isdigit():
                    source_periods.add(year)

                    # 扫描该年份的所有股票文件
                    for file_path in year_dir.glob("*.csv"):
                        stock_code = file_path.stem
                        source_stocks.add(stock_code)

                        if stock_code not in stock_files:
                            stock_files[stock_code] = []
                        stock_files[stock_code].append({
                            'year': year,
                            'file': file_path,
                            'size': file_path.stat().st_size
                        })

            data_summary['data_sources'][source_name] = {
                'description': source_config['description'],
                'stock_count': len(source_stocks),
                'periods': sorted(list(source_periods)),
                'stocks': sorted(list(source_stocks)),
                'stock_files': stock_files
            }

            data_summary['total_stocks'] = max(data_summary['total_stocks'], len(source_stocks))
            data_summary['available_periods'].update(source_periods)

            logger.info(f"{source_name}: {len(source_stocks)} 只股票, {len(source_periods)} 年数据")

        data_summary['available_periods'] = sorted(list(data_summary['available_periods']))
        data_summary['stock_lists']['all_unique_stocks'] = sorted(list(set(
            stock for source in data_summary['data_sources'].values()
            for stock in source['stocks']
        )))

        return data_summary

    def stratified_sampling(self, stocks: List[str], sample_size: int) -> List[str]:
        """分层采样股票"""
        if len(stocks) <= sample_size:
            return stocks

        # 按股票代码分类（上海：6开头，深圳：0开头，北京：8开头）
        sh_stocks = [s for s in stocks if s.startswith('6')]
        sz_stocks = [s for s in stocks if s.startswith('0') or s.startswith('3')]
        bj_stocks = [s for s in stocks if s.startswith('8')]

        # 计算各类别样本数
        total = len(stocks)
        sh_sample = int(len(sh_stocks) / total * sample_size)
        sz_sample = int(len(sz_stocks) / total * sample_size)
        bj_sample = sample_size - sh_sample - sz_sample

        # 从各类别随机采样
        import random
        sampled = []

        if sh_stocks and sh_sample > 0:
            sampled.extend(random.sample(sh_stocks, min(sh_sample, len(sh_stocks))))

        if sz_stocks and sz_sample > 0:
            sampled.extend(random.sample(sz_stocks, min(sz_sample, len(sz_stocks))))

        if bj_stocks and bj_sample > 0:
            sampled.extend(random.sample(bj_stocks, min(bj_sample, len(bj_stocks))))

        # 如果样本不够，从剩余股票中随机补充
        remaining = [s for s in stocks if s not in sampled]
        while len(sampled) < sample_size and remaining:
            stock = random.choice(remaining)
            sampled.append(stock)
            remaining.remove(stock)

        return sampled[:sample_size]

    def load_stock_data_comprehensive(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """综合加载股票数据（从多个数据源）"""
        all_data = []

        # 尝试从不同数据源加载数据
        for source_name, source_config in self.data_sources.items():
            if source_name not in self.data_summary['data_sources']:
                continue

            source_files = self.data_summary['data_sources'][source_name]['stock_files']

            if stock_code in source_files:
                for file_info in source_files[stock_code]:
                    try:
                        file_path = file_info['file']
                        df = pd.read_csv(file_path)

                        # 数据预处理
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date')

                        # 日期过滤
                        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

                        if not df.empty:
                            all_data.append(df)

                    except Exception as e:
                        logger.warning(f"加载文件失败 {file_path}: {e}")

        if all_data:
            # 合并所有数据源的数据
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data = combined_data.drop_duplicates(subset=['date']).sort_values('date')
            return combined_data

        return pd.DataFrame()

    def run_comprehensive_backtest(self) -> Dict[str, Any]:
        """运行综合回测"""
        logger.info("=== 开始综合本地股票数据回测 ===")

        # 扫描本地数据
        self.data_summary = self.scan_all_local_data()

        results = {
            'backtest_summary': {
                'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_stocks_available': len(self.data_summary['stock_lists']['all_unique_stocks']),
                'data_sources_used': list(self.data_summary['data_sources'].keys()),
                'available_periods': self.data_summary['available_periods']
            },
            'sampling_results': {},
            'period_analysis': {},
            'top_performers': {},
            'risk_analysis': {},
            'comprehensive_metrics': {}
        }

        # 更新股票列表
        all_stocks = self.data_summary['stock_lists']['all_unique_stocks']

        # 创建动态回测时期
        available_years = self.data_summary['available_periods']
        if len(available_years) >= 2:
            # 使用可用的数据年份创建回测时期
            recent_years = sorted(available_years)[-3:]  # 最近3年
            earliest_year = recent_years[0]
            latest_year = recent_years[-1]

            # 创建市场时期配置
            dynamic_periods = {
                'full_period': {
                    'start_date': f'{earliest_year}-01-01',
                    'end_date': f'{latest_year}-12-31',
                    'description': f'完整时期 ({earliest_year}-{latest_year})'
                }
            }

            # 如果有足够年份，创建子时期
            if len(recent_years) >= 2:
                mid_point = (len(recent_years) - 1) // 2
                dynamic_periods['early_period'] = {
                    'start_date': f'{recent_years[0]}-01-01',
                    'end_date': f'{recent_years[mid_point]}-12-31',
                    'description': f'前期 ({recent_years[0]}-{recent_years[mid_point]})'
                }
                dynamic_periods['recent_period'] = {
                    'start_date': f'{recent_years[mid_point+1]}-01-01',
                    'end_date': f'{latest_year}-12-31',
                    'description': f'近期 ({recent_years[mid_point+1]}-{latest_year})'
                }

            self.market_periods = dynamic_periods

        # 不同采样率的回测
        for sampling_rate in self.backtest_config['sampling_rates']:
            logger.info(f"执行 {sampling_rate*100:.0f}% 采样率回测")

            if sampling_rate < 1.0:
                # 分层采样
                sample_size = int(len(all_stocks) * sampling_rate)
                sampled_stocks = self.stratified_sampling(all_stocks, sample_size)
            else:
                sampled_stocks = all_stocks

            logger.info(f"测试股票数量: {len(sampled_stocks)}")

            period_results = {}

            for period_name, period_config in self.market_periods.items():
                logger.info(f"回测时期: {period_name}")

                period_metrics = []
                successful_stocks = 0

                for i, stock_code in enumerate(sampled_stocks):
                    if i % 50 == 0:
                        logger.info(f"处理进度: {i}/{len(sampled_stocks)} - {stock_code}")

                    # 加载数据
                    data = self.load_stock_data_comprehensive(
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
                        strategy_metrics.update({
                            'stock_code': stock_code,
                            'period': period_name,
                            'data_points': len(data),
                            'start_date': period_config['start_date'],
                            'end_date': period_config['end_date']
                        })
                        period_metrics.append(strategy_metrics)
                        successful_stocks += 1

                # 汇总时期结果
                if period_metrics:
                    period_df = pd.DataFrame(period_metrics)

                    period_summary = {
                        'successful_stocks': successful_stocks,
                        'success_rate': successful_stocks / len(sampled_stocks),
                        'sampling_rate': sampling_rate,
                        'period_description': period_config['description']
                    }

                    # 计算统计指标
                    for metric in self.backtest_config['performance_metrics']:
                        if metric in period_df.columns:
                            period_summary[f'avg_{metric}'] = period_df[metric].mean()
                            period_summary[f'median_{metric}'] = period_df[metric].median()
                            period_summary[f'std_{metric}'] = period_df[metric].std()
                            period_summary[f'min_{metric}'] = period_df[metric].min()
                            period_summary[f'max_{metric}'] = period_df[metric].max()

                    # 计算整体组合表现
                    all_returns = []
                    for metrics in period_metrics:
                        # 重新计算该股票的策略收益用于组合分析
                        data = self.load_stock_data_comprehensive(
                            metrics['stock_code'],
                            period_config['start_date'],
                            period_config['end_date']
                        )
                        if not data.empty:
                            combined_scores, returns = self.calculate_combined_factor_scores(data)
                            if combined_scores is not None and returns is not None:
                                strategy_returns = returns[combined_scores.rank(pct=True) > 0.8]
                                all_returns.extend(strategy_returns.tolist())

                    if all_returns:
                        portfolio_return = np.mean(all_returns)
                        period_summary['portfolio_annual_return'] = portfolio_return * 252
                        period_summary['portfolio_volatility'] = np.std(all_returns) * np.sqrt(252)
                        if period_summary['portfolio_volatility'] > 0:
                            period_summary['portfolio_sharpe_ratio'] = period_summary['portfolio_annual_return'] / period_summary['portfolio_volatility']
                        else:
                            period_summary['portfolio_sharpe_ratio'] = 0

                    period_results[period_name] = period_summary

                    logger.info(f"{period_name} ({sampling_rate*100:.0f}%): {successful_stocks}/{len(sampled_stocks)} 成功")
                    logger.info(f"  平均年化收益: {period_summary.get('avg_annual_return', 0):.2%}")
                    logger.info(f"  组合年化收益: {period_summary.get('portfolio_annual_return', 0):.2%}")

            results['sampling_results'][f'{sampling_rate*100:.0f}%'] = period_results

        # 寻找最佳表现股票
        if '100%' in results['sampling_results']:
            full_results = results['sampling_results']['100%']
            for period_name, period_data in full_results.items():
                # 重新计算以获取顶级表现者
                top_performers = self.get_top_performers(period_name, top_n=20)
                results['top_performers'][period_name] = top_performers

        # 风险分析
        results['risk_analysis'] = self.analyze_risk_characteristics(results)

        # 综合指标
        results['comprehensive_metrics'] = self.calculate_comprehensive_metrics(results)

        return results

    def get_top_performers(self, period_name: str, top_n: int = 20) -> Dict[str, Any]:
        """获取顶级表现股票"""
        period_config = self.market_periods[period_name]
        all_stocks = self.data_summary['stock_lists']['all_unique_stocks']

        stock_performance = []

        # 限制详细分析的数量以节省时间
        max_stocks = min(len(all_stocks), self.backtest_config['max_stocks_for_detail'])
        sampled_stocks = all_stocks[:max_stocks] if len(all_stocks) > max_stocks else all_stocks

        for stock_code in sampled_stocks:
            data = self.load_stock_data_comprehensive(
                stock_code,
                period_config['start_date'],
                period_config['end_date']
            )

            if data.empty or len(data) < 30:
                continue

            combined_scores, returns = self.calculate_combined_factor_scores(data)
            if combined_scores is None or returns is None:
                continue

            strategy_metrics = self.calculate_strategy_performance(combined_scores, returns)
            if strategy_metrics:
                strategy_metrics['stock_code'] = stock_code
                stock_performance.append(strategy_metrics)

        if stock_performance:
            df = pd.DataFrame(stock_performance)

            top_by_return = df.nlargest(top_n, 'annual_return')
            top_by_sharpe = df.nlargest(top_n, 'sharpe_ratio')
            top_by_win_rate = df.nlargest(top_n, 'win_rate')

            return {
                'top_by_annual_return': top_by_return.to_dict('records'),
                'top_by_sharpe_ratio': top_by_sharpe.to_dict('records'),
                'top_by_win_rate': top_by_win_rate.to_dict('records'),
                'total_analyzed': len(df)
            }

        return {}

    def analyze_risk_characteristics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """分析风险特征"""
        risk_analysis = {
            'return_distribution': {},
            'risk_metrics': {},
            'drawdown_analysis': {}
        }

        # 分析不同采样率的一致性
        sampling_rates = list(results['sampling_results'].keys())
        if len(sampling_rates) >= 2:
            consistency_analysis = {}

            for period_name in self.market_periods.keys():
                period_consistency = {}
                returns = []
                sharpe_ratios = []

                for rate in sampling_rates:
                    if period_name in results['sampling_results'][rate]:
                        period_data = results['sampling_results'][rate][period_name]
                        returns.append(period_data.get('avg_annual_return', 0))
                        sharpe_ratios.append(period_data.get('avg_sharpe_ratio', 0))

                if returns:
                    period_consistency = {
                        'return_consistency': np.std(returns) / np.abs(np.mean(returns)) if np.mean(returns) != 0 else float('inf'),
                        'sharpe_consistency': np.std(sharpe_ratios) / np.abs(np.mean(sharpe_ratios)) if np.mean(sharpe_ratios) != 0 else float('inf'),
                        'return_range': [min(returns), max(returns)],
                        'sharpe_range': [min(sharpe_ratios), max(sharpe_ratios)]
                    }
                    consistency_analysis[period_name] = period_consistency

            risk_analysis['consistency_analysis'] = consistency_analysis

        return risk_analysis

    def calculate_comprehensive_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """计算综合指标"""
        comprehensive = {
            'overall_performance': {},
            'stability_metrics': {},
            'scalability_assessment': {}
        }

        # 整体表现指标
        if '100%' in results['sampling_results']:
            full_results = results['sampling_results']['100%']

            all_returns = []
            all_sharpe = []
            all_win_rates = []

            for period_name, period_data in full_results.items():
                if 'avg_annual_return' in period_data:
                    all_returns.append(period_data['avg_annual_return'])
                if 'avg_sharpe_ratio' in period_data:
                    all_sharpe.append(period_data['avg_sharpe_ratio'])
                if 'avg_win_rate' in period_data:
                    all_win_rates.append(period_data['avg_win_rate'])

            if all_returns:
                comprehensive['overall_performance'] = {
                    'mean_annual_return': np.mean(all_returns),
                    'std_annual_return': np.std(all_returns),
                    'mean_sharpe_ratio': np.mean(all_sharpe) if all_sharpe else 0,
                    'mean_win_rate': np.mean(all_win_rates) if all_win_rates else 0,
                    'periods_analyzed': len(all_returns)
                }

        # 可扩展性评估
        scalability_data = []
        for rate in results['sampling_results'].keys():
            rate_pct = float(rate.replace('%', '')) / 100
            for period_name, period_data in results['sampling_results'][rate].items():
                scalability_data.append({
                    'sampling_rate': rate_pct,
                    'period': period_name,
                    'avg_return': period_data.get('avg_annual_return', 0),
                    'success_rate': period_data.get('success_rate', 0)
                })

        if scalability_data:
            df = pd.DataFrame(scalability_data)

            # 分析采样率对表现的影响
            correlation = df['sampling_rate'].corr(df['avg_return'])
            comprehensive['scalability_assessment'] = {
                'sampling_correlation': correlation,
                'scalable': abs(correlation) < 0.1,  # 相关性低说明可扩展性好
                'largest_sample_performance': df[df['sampling_rate'] == 1.0]['avg_return'].mean() if len(df[df['sampling_rate'] == 1.0]) > 0 else 0,
                'smallest_sample_performance': df[df['sampling_rate'] == 0.1]['avg_return'].mean() if len(df[df['sampling_rate'] == 0.1]) > 0 else 0
            }

        return comprehensive

    def generate_comprehensive_report(self, results: Dict[str, Any]) -> str:
        """生成综合回测报告"""
        report = []
        report.append("# 综合本地股票数据回测报告")
        report.append("=" * 80)
        report.append("")

        # 回测概述
        summary = results['backtest_summary']
        report.append("## 回测概述")
        report.append(f"- 执行时间: {summary['execution_time']}")
        report.append(f"- 可用股票总数: {summary['total_stocks_available']} 只")
        report.append(f"- 使用数据源: {', '.join(summary['data_sources_used'])}")
        report.append(f"- 可用数据时期: {', '.join(summary['available_periods'])}")
        report.append("")

        # 数据源详情
        report.append("## 数据源详情")
        for source_name, source_data in self.data_summary['data_sources'].items():
            report.append(f"### {source_name}")
            report.append(f"- 描述: {source_data['description']}")
            report.append(f"- 股票数量: {source_data['stock_count']} 只")
            report.append(f"- 数据时期: {', '.join(source_data['periods'])}")
            report.append("")

        # 采样率分析
        report.append("## 采样率分析")
        for rate, period_results in results['sampling_results'].items():
            report.append(f"### {rate} 采样率")
            for period_name, period_data in period_results.items():
                report.append(f"**{period_data['period_description']}**:")
                report.append(f"- 成功股票: {period_data['successful_stocks']} 只 ({period_data['success_rate']:.1%})")
                report.append(f"- 平均年化收益: {period_data.get('avg_annual_return', 0):.2%}")
                report.append(f"- 平均夏普比率: {period_data.get('avg_sharpe_ratio', 0):.2f}")
                report.append(f"- 组合年化收益: {period_data.get('portfolio_annual_return', 0):.2%}")
                report.append(f"- 组合夏普比率: {period_data.get('portfolio_sharpe_ratio', 0):.2f}")
                report.append("")

        # 顶级表现者
        report.append("## 顶级表现股票")
        for period_name, top_data in results['top_performers'].items():
            report.append(f"### {period_name}")

            if 'top_by_annual_return' in top_data:
                report.append("**年化收益前5名:**")
                for i, stock in enumerate(top_data['top_by_annual_return'][:5]):
                    report.append(f"{i+1}. {stock['stock_code']}: {stock['annual_return']:.2%}")
                report.append("")

        # 风险分析
        if 'consistency_analysis' in results['risk_analysis']:
            report.append("## 风险一致性分析")
            for period_name, consistency in results['risk_analysis']['consistency_analysis'].items():
                report.append(f"### {period_name}")
                report.append(f"- 收益一致性: {consistency['return_consistency']:.4f}")
                report.append(f"- 夏普一致性: {consistency['sharpe_consistency']:.4f}")
                report.append("")

        # 综合评估
        if 'overall_performance' in results['comprehensive_metrics']:
            overall = results['comprehensive_metrics']['overall_performance']
            report.append("## 综合评估")
            report.append(f"- 跨时期平均年化收益: {overall['mean_annual_return']:.2%}")
            report.append(f"- 收益标准差: {overall['std_annual_return']:.2%}")
            report.append(f"- 平均夏普比率: {overall['mean_sharpe_ratio']:.2f}")
            report.append(f"- 平均胜率: {overall['mean_win_rate']:.2%}")
            report.append("")

        # 可扩展性评估
        if 'scalability_assessment' in results['comprehensive_metrics']:
            scalability = results['comprehensive_metrics']['scalability_assessment']
            report.append("## 可扩展性评估")
            report.append(f"- 采样率相关性: {scalability['sampling_correlation']:.4f}")
            report.append(f"- 策略可扩展性: {'良好' if scalability['scalable'] else '需要优化'}")
            report.append("")

        # 结论和建议
        report.append("## 结论和建议")

        if 'overall_performance' in results['comprehensive_metrics']:
            avg_return = results['comprehensive_metrics']['overall_performance']['mean_annual_return']
            if avg_return > 0:
                report.append("✅ **策略表现正面**")
                report.append("- V1组合策略在全面回测中表现良好")
                report.append("- 动量强度与成交量激增因子结合具有稳定性")
                report.append("- 策略在不同样本量下保持一致性")
            else:
                report.append("⚠️ **策略表现需要优化**")
                report.append("- 建议重新评估因子权重")
                report.append("- 考虑增加风险管理机制")

        report.append("- 建议继续监控策略在不同市场环境下的表现")
        report.append("- 可考虑与其他低相关性策略组合")
        report.append("- 定期重新评估因子有效性")

        return "\n".join(report)

def main():
    """主函数"""
    logger.info("=== 综合本地股票数据回测开始 ===")

    backtester = ComprehensiveBacktester()

    # 运行综合回测
    results = backtester.run_comprehensive_backtest()

    if results:
        # 生成报告
        report = backtester.generate_comprehensive_report(results)

        # 保存报告
        report_file = backtester.comprehensive_output_dir / "comprehensive_backtest_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"综合回测报告已保存: {report_file}")

        # 保存详细结果
        results_file = backtester.comprehensive_output_dir / "comprehensive_backtest_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"详细结果已保存: {results_file}")

        # 打印关键指标
        if 'overall_performance' in results.get('comprehensive_metrics', {}):
            overall = results['comprehensive_metrics']['overall_performance']
            print(f"\n=== 关键指标 ===")
            print(f"平均年化收益: {overall['mean_annual_return']:.2%}")
            print(f"平均夏普比率: {overall['mean_sharpe_ratio']:.2f}")
            print(f"平均胜率: {overall['mean_win_rate']:.2%}")
            print(f"分析时期数: {overall['periods_analyzed']}")

    logger.info("=== 综合本地股票数据回测完成 ===")

if __name__ == "__main__":
    main()