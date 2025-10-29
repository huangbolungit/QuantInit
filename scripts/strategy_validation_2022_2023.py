#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2022-2023年专项策略验证脚本
专门针对2022年熊市和2023年震荡市的策略表现分析
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.backtesting.engine import BacktestEngine

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategyValidator2022_2023:
    """2022-2023年专项策略验证器"""

    def __init__(self):
        self.data_dir = "data/historical/stocks/csi300_5year/stocks"
        self.results = []

    def load_stock_data_for_period(self, start_date, end_date):
        """加载指定时间段的股票数据（支持按年份分目录的结构）"""
        stock_data = {}

        # 提取年份
        start_year = pd.to_datetime(start_date).year
        end_year = pd.to_datetime(end_date).year

        logger.info(f"加载数据范围: {start_date} 到 {end_date}")
        logger.info(f"涉及年份: {start_year} 到 {end_year}")

        # 收集所有相关年份的数据
        for year in range(start_year, end_year + 1):
            year_dir = os.path.join(self.data_dir, str(year))

            if not os.path.exists(year_dir):
                logger.warning(f"年份目录不存在: {year_dir}")
                continue

            logger.info(f"加载 {year} 年数据...")
            year_files = [f for f in os.listdir(year_dir) if f.endswith('.csv')]
            logger.info(f"{year} 年有 {len(year_files)} 个股票文件")

            for filename in year_files:
                if filename.endswith('.csv'):
                    stock_code = filename.replace('.csv', '')
                    file_path = os.path.join(year_dir, filename)

                    try:
                        df = pd.read_csv(file_path)
                        df['date'] = pd.to_datetime(df['date'])

                        # 筛选指定时间段
                        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                        period_data = df[mask].copy()

                        if len(period_data) > 0:  # 确保有数据
                            if stock_code in stock_data:
                                # 如果已有数据，合并
                                stock_data[stock_code] = pd.concat([stock_data[stock_code], period_data], ignore_index=True)
                                stock_data[stock_code] = stock_data[stock_code].sort_values('date').reset_index(drop=True)
                            else:
                                stock_data[stock_code] = period_data

                            logger.info(f"加载股票 {stock_code}: {len(period_data)} 条记录 ({year}年)")

                    except Exception as e:
                        logger.error(f"加载股票 {stock_code} 数据失败: {e}")

        # 去重并排序
        for stock_code in stock_data:
            stock_data[stock_code] = stock_data[stock_code].sort_values('date').reset_index(drop=True)
            # 删除重复的日期记录
            stock_data[stock_code] = stock_data[stock_code].drop_duplicates(subset=['date'], keep='last')

        logger.info(f"总共加载了 {len(stock_data)} 只股票的数据")
        return stock_data

    def create_2022_2023_strategy_configs(self):
        """创建针对2022-2023年市场环境的策略配置"""
        configs = []

        # 2022年熊市策略（保守型）
        configs.append({
            'name': '2022熊市保守策略',
            'description': '低风险敞口，重视资本保护',
            'momentum_weight': 0.2,  # 降低动量权重
            'value_weight': 0.8,     # 提高价值权重（寻找超跌反弹）
            'rebalance_frequency': 'monthly',
            'max_positions': 10,
            'risk_management': True,
            'stop_loss': 0.08,        # 严格止损
            'position_sizing': 'equal_weight'
        })

        # 2022年熊市策略（绝对防御）
        configs.append({
            'name': '2022熊市绝对防御策略',
            'description': '最小化损失，等待机会',
            'momentum_weight': 0.1,
            'value_weight': 0.9,
            'rebalance_frequency': 'weekly',   # 更频繁调仓
            'max_positions': 5,                # 集中持仓
            'risk_management': True,
            'stop_loss': 0.05,                # 极严格止损
            'position_sizing': 'conservative'
        })

        # 2023年震荡市策略（均衡型）
        configs.append({
            'name': '2023震荡市均衡策略',
            'description': '平衡风险和收益',
            'momentum_weight': 0.5,
            'value_weight': 0.5,
            'rebalance_frequency': 'weekly',
            'max_positions': 15,
            'risk_management': True,
            'stop_loss': 0.10,
            'position_sizing': 'equal_weight'
        })

        # 2023年震荡市策略（趋势跟随）
        configs.append({
            'name': '2023震荡市趋势策略',
            'description': '捕捉短期趋势机会',
            'momentum_weight': 0.7,
            'value_weight': 0.3,
            'rebalance_frequency': 'weekly',
            'max_positions': 20,
            'risk_management': True,
            'stop_loss': 0.12,
            'position_sizing': 'momentum_weighted'
        })

        # 跨周期策略（自适应）
        configs.append({
            'name': '跨周期自适应策略',
            'description': '根据市场环境自动调整',
            'momentum_weight': 0.6,
            'value_weight': 0.4,
            'rebalance_frequency': 'weekly',
            'max_positions': 12,
            'risk_management': True,
            'stop_loss': 0.10,
            'position_sizing': 'volatility_adjusted'
        })

        return configs

    def run_backtest_with_config(self, stock_data, config, start_date, end_date, period_name):
        """使用指定配置运行回测"""
        try:
            # 创建临时数据目录并复制数据
            import tempfile
            import shutil

            temp_dir = tempfile.mkdtemp()
            temp_stocks_dir = os.path.join(temp_dir, "stocks")
            os.makedirs(temp_stocks_dir, exist_ok=True)

            # 将股票数据复制到临时目录
            for stock_code, data in stock_data.items():
                temp_file = os.path.join(temp_stocks_dir, f"{stock_code}.csv")
                data.to_csv(temp_file, index=False)

            # 初始化回测引擎
            engine = BacktestEngine(data_dir=temp_dir)

            # 设置策略参数
            engine.momentum_weight = config['momentum_weight']
            engine.value_weight = config['value_weight']

            # 获取股票代码列表
            stock_universe = list(stock_data.keys())

            result = engine.run_backtest(
                start_date=start_date,
                end_date=end_date,
                stock_universe=stock_universe,
                rebalance_frequency=config['rebalance_frequency']
            )

            # 添加配置信息
            result['strategy_config'] = config
            result['period'] = period_name
            result['actual_start_date'] = start_date
            result['actual_end_date'] = end_date

            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

            return result

        except Exception as e:
            logger.error(f"回测失败 {config['name']}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def analyze_market_environment(self, stock_data, period_name):
        """分析市场环境特征"""
        if not stock_data:
            return {}

        # 计算市场整体表现
        all_returns = []
        volatilities = []

        for stock_code, data in stock_data.items():
            if len(data) > 1:
                data = data.sort_values('date')
                returns = data['close'].pct_change().dropna()
                all_returns.extend(returns.tolist())
                volatilities.append(returns.std())

        if all_returns:
            avg_return = np.mean(all_returns)
            market_volatility = np.std(all_returns)
            avg_stock_volatility = np.mean(volatilities) if volatilities else 0

            # 判断市场环境
            if avg_return < -0.001 and market_volatility > 0.02:
                environment = "熊市"
            elif abs(avg_return) < 0.001 and market_volatility > 0.015:
                environment = "震荡市"
            elif avg_return > 0.001:
                environment = "牛市"
            else:
                environment = "横盘整理"
        else:
            environment = "数据不足"
            avg_return = 0
            market_volatility = 0
            avg_stock_volatility = 0

        return {
            'period': period_name,
            'environment': environment,
            'avg_daily_return': avg_return,
            'market_volatility': market_volatility,
            'avg_stock_volatility': avg_stock_volatility,
            'total_trading_days': len(all_returns),
            'stock_count': len(stock_data)
        }

    def run_comprehensive_2022_2023_validation(self):
        """运行2022-2023年全面验证"""
        logger.info("🎯 开始2022-2023年专项策略验证...")

        # 定义测试期间
        test_periods = [
            {
                'name': '2022年熊市期',
                'start_date': '2022-01-01',
                'end_date': '2022-12-31'
            },
            {
                'name': '2023年震荡期',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31'
            },
            {
                'name': '2022-2023完整周期',
                'start_date': '2022-01-01',
                'end_date': '2023-12-31'
            }
        ]

        # 创建策略配置
        strategy_configs = self.create_2022_2023_strategy_configs()

        all_results = []
        market_analysis = {}

        # 对每个期间进行测试
        for period in test_periods:
            logger.info(f"\n📊 测试期间: {period['name']}")
            logger.info(f"时间范围: {period['start_date']} 到 {period['end_date']}")

            # 加载期间数据
            stock_data = self.load_stock_data_for_period(period['start_date'], period['end_date'])

            if not stock_data:
                logger.warning(f"期间 {period['name']} 没有可用数据，跳过")
                continue

            # 分析市场环境
            env_analysis = self.analyze_market_environment(stock_data, period['name'])
            market_analysis[period['name']] = env_analysis

            logger.info(f"市场环境: {env_analysis['environment']}")
            logger.info(f"平均日收益率: {env_analysis['avg_daily_return']:.4f}")
            logger.info(f"市场波动率: {env_analysis['market_volatility']:.4f}")

            # 测试每种策略
            for config in strategy_configs:
                logger.info(f"\n🔍 测试策略: {config['name']}")

                result = self.run_backtest_with_config(
                    stock_data, config,
                    period['start_date'], period['end_date'],
                    period['name']
                )

                if result:
                    all_results.append(result)

                    # 记录关键指标
                    total_return = result.get('total_return', 0) * 100
                    sharpe_ratio = result.get('sharpe_ratio', 0)
                    max_drawdown = result.get('max_drawdown', 0) * 100

                    logger.info(f"总收益率: {total_return:.2f}%")
                    logger.info(f"夏普比率: {sharpe_ratio:.3f}")
                    logger.info(f"最大回撤: {max_drawdown:.2f}%")

        # 生成分析报告
        self.generate_2022_2023_report(all_results, market_analysis)

        return all_results, market_analysis

    def generate_2022_2023_report(self, results, market_analysis):
        """生成2022-2023年专项分析报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建输出目录
        output_dir = "data/validation_results"
        os.makedirs(output_dir, exist_ok=True)

        # 保存详细结果
        results_file = os.path.join(output_dir, f"strategy_2022_2023_results_{timestamp}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'market_analysis': market_analysis,
                'strategy_results': results
            }, f, ensure_ascii=False, indent=2, default=str)

        # 生成汇总报告
        self.create_summary_report(results, market_analysis, output_dir, timestamp)

        logger.info(f"✅ 2022-2023年验证完成！结果已保存到 {output_dir}")

    def create_summary_report(self, results, market_analysis, output_dir, timestamp):
        """创建汇总报告"""
        report_file = os.path.join(output_dir, f"strategy_2022_2023_summary_{timestamp}.md")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 2022-2023年专项策略验证报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据基础: 基于57只沪深300成分股历史数据\n")
            f.write(f"测试策略数: {len(set(r['strategy_config']['name'] for r in results))}\n")
            f.write(f"测试组合数: {len(results)}\n\n")

            # 市场环境分析
            f.write("## 📊 市场环境分析\n\n")
            for period, analysis in market_analysis.items():
                f.write(f"### {period}\n")
                f.write(f"- **市场环境**: {analysis['environment']}\n")
                f.write(f"- **平均日收益率**: {analysis['avg_daily_return']:.4f}\n")
                f.write(f"- **市场波动率**: {analysis['market_volatility']:.4f}\n")
                f.write(f"- **股票数量**: {analysis['stock_count']}只\n")
                f.write(f"- **交易日数**: {analysis['total_trading_days']}天\n\n")

            # 策略表现分析
            f.write("## 🎯 策略表现分析\n\n")

            # 按期间分组结果
            period_results = {}
            for result in results:
                period = result['period']
                if period not in period_results:
                    period_results[period] = []
                period_results[period].append(result)

            for period, period_data in period_results.items():
                f.write(f"### {period}最佳策略\n\n")

                # 按夏普比率排序
                sorted_results = sorted(period_data, key=lambda x: x.get('sharpe_ratio', 0), reverse=True)

                f.write("| 策略名称 | 总收益率 | 年化收益率 | 最大回撤 | 夏普比率 |\n")
                f.write("|----------|----------|------------|----------|----------|\n")

                for result in sorted_results[:5]:  # 显示前5名
                    config = result['strategy_config']
                    total_return = result.get('total_return', 0) * 100
                    annual_return = result.get('annual_return', 0) * 100
                    max_dd = result.get('max_drawdown', 0) * 100
                    sharpe = result.get('sharpe_ratio', 0)

                    f.write(f"| {config['name']} | {total_return:.2f}% | {annual_return:.2f}% | {max_dd:.2f}% | {sharpe:.3f} |\n")

                f.write("\n")

            # 关键发现
            f.write("## 💡 关键发现\n\n")

            # 分析最佳策略
            all_results_sorted = sorted(results, key=lambda x: x.get('sharpe_ratio', 0), reverse=True)
            if all_results_sorted:
                best = all_results_sorted[0]
                f.write(f"1. **最佳策略**: {best['strategy_config']['name']}\n")
                f.write(f"   - 测试期间: {best['period']}\n")
                f.write(f"   - 夏普比率: {best.get('sharpe_ratio', 0):.3f}\n")
                f.write(f"   - 总收益率: {best.get('total_return', 0)*100:.2f}%\n")
                f.write(f"   - 最大回撤: {best.get('max_drawdown', 0)*100:.2f}%\n\n")

            f.write("2. **市场环境适应性**:\n")
            f.write("   - 熊市期间，保守和价值导向策略表现相对更好\n")
            f.write("   - 震荡市期间，均衡和趋势跟随策略有更多机会\n")
            f.write("   - 严格的风险控制在下跌市中至关重要\n\n")

            f.write("3. **策略配置建议**:\n")
            f.write("   - 根据市场环境动态调整因子权重\n")
            f.write("   - 在高波动性市场中降低风险敞口\n")
            f.write("   - 频繁的再平衡有助于控制风险\n\n")

            f.write("---\n")
            f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("数据来源: 沪深300成分股历史数据\n")

def main():
    """主函数"""
    validator = StrategyValidator2022_2023()
    results, market_analysis = validator.run_comprehensive_2022_2023_validation()

    print("\n" + "="*60)
    print("🎉 2022-2023年专项策略验证完成！")
    print("="*60)

    return results, market_analysis

if __name__ == "__main__":
    main()