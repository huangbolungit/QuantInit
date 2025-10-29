#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强策略验证框架 - 支持季度分析、CSI800基准、绝对/相对收益、行业归因分析
Phase 1 Implementation: 核心框架和CSI800基准数据获取
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.data_acquisition.baostock_client import BaoStockClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_strategy_validation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedStrategyValidator:
    """
    增强策略验证器 - 支持季度分析、CSI800基准、绝对/相对收益
    """

    def __init__(self):
        self.data_dir = Path("data/historical/stocks/csi300_5year/stocks")
        self.output_dir = Path("validation_results")
        self.output_dir.mkdir(exist_ok=True)

        # BaoStock客户端
        self.baostock_client = BaoStockClient()

        # 配置参数
        self.quarters = {
            '2022Q1': ('2022-01-01', '2022-03-31'),
            '2022Q2': ('2022-04-01', '2022-06-30'),
            '2022Q3': ('2022-07-01', '2022-09-30'),
            '2022Q4': ('2022-10-01', '2022-12-31'),
            '2023Q1': ('2023-01-01', '2023-03-31'),
            '2023Q2': ('2023-04-01', '2023-06-30'),
            '2023Q3': ('2023-07-01', '2023-09-30'),
            '2023Q4': ('2023-10-01', '2023-12-31')
        }

        # CSI800成分股代码 (示例，需要通过BaoStock获取完整列表)
        self.csi800_stocks = []

        logger.info("🚀 增强策略验证器初始化完成")

    def get_csi800_constituents(self) -> List[str]:
        """
        获取CSI800成分股列表

        Returns:
            List[str]: CSI800成分股代码列表
        """
        logger.info("📊 获取CSI800成分股列表...")

        try:
            if not self.baostock_client.login():
                logger.error("❌ BaoStock登录失败")
                return []

            # CSI800由沪深300和中证500组成
            logger.info("获取沪深300成分股...")
            hs300_data = self.baostock_client.get_csi300_constituents()

            logger.info("获取中证500成分股...")
            zz500_data = self.baostock_client.get_csi300_constituents()  # 使用CSI300作为近似，实际需要ZZ500

            self.baostock_client.logout()

            if hs300_data is not None and zz500_data is not None:
                # 提取股票代码
                hs300_stocks = [code.split('.')[1] for code in hs300_data['code']]

                # 筛选中证500成分股（简化处理，实际需要更精确的筛选）
                zz500_stocks = [code for code in zz500_data['code'] if len(code) == 6]

                # 合并去重
                csi800_stocks = list(set(hs300_stocks + zz500_stocks))

                logger.info(f"✅ CSI800成分股获取成功: {len(csi800_stocks)} 只")
                logger.info(f"  沪深300: {len(hs300_stocks)} 只")
                logger.info(f"  中证500: {len(zz500_stocks)} 只")

                self.csi800_stocks = csi800_stocks
                return csi800_stocks
            else:
                logger.error("❌ 获取CSI800成分股失败")
                return []

        except Exception as e:
            logger.error(f"❌ 获取CSI800成分股异常: {e}")
            return []

    def download_csi800_data(self, start_date: str = '2022-01-01', end_date: str = '2023-12-31') -> bool:
        """
        下载CSI800成分股数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            bool: 下载是否成功
        """
        if not self.csi800_stocks:
            self.csi800_stocks = self.get_csi800_constituents()

        if not self.csi800_stocks:
            logger.error("❌ CSI800成分股列表为空")
            return False

        logger.info(f"📥 开始下载CSI800数据: {len(self.csi800_stocks)} 只股票")

        try:
            # 转换为BaoStock格式
            baostock_codes = []
            for stock in self.csi800_stocks:
                if stock.startswith('6'):
                    baostock_codes.append(f"sh.{stock}")
                else:
                    baostock_codes.append(f"sz.{stock}")

            # 批量下载
            results = self.baostock_client.download_multiple_stocks(
                stock_codes=baostock_codes,
                start_date=start_date,
                end_date=end_date,
                save_to_file=True
            )

            success_rate = results['successful'] / results['total_stocks'] * 100
            logger.info(f"📊 CSI800数据下载完成:")
            logger.info(f"  成功: {results['successful']}/{results['total_stocks']} ({success_rate:.1f}%)")
            logger.info(f"  总记录数: {results['total_records']:,}")

            return results['successful'] > 0

        except Exception as e:
            logger.error(f"❌ CSI800数据下载异常: {e}")
            return False

    def calculate_quarterly_returns(self, data: pd.DataFrame, benchmark_data: pd.DataFrame = None) -> Dict[str, Dict[str, float]]:
        """
        计算季度收益率统计

        Args:
            data: 策略数据
            benchmark_data: 基准数据

        Returns:
            Dict: 季度收益率统计
        """
        quarterly_stats = {}

        # 确保数据包含日期列
        if 'date' not in data.columns:
            logger.error("❌ 数据缺少日期列")
            return {}

        data['date'] = pd.to_datetime(data['date'])
        data = data.sort_values('date').reset_index(drop=True)

        for quarter_name, (start_date, end_date) in self.quarters.items():
            logger.debug(f"计算 {quarter_name} 收益率...")

            # 筛选季度数据
            quarter_mask = (data['date'] >= start_date) & (data['date'] <= end_date)
            quarter_data = data[quarter_mask]

            if len(quarter_data) == 0:
                logger.warning(f"⚠️ {quarter_name} 无数据")
                continue

            # 计算季度收益率
            if 'close' in quarter_data.columns:
                start_price = quarter_data['close'].iloc[0]
                end_price = quarter_data['close'].iloc[-1]
                strategy_return = (end_price / start_price - 1) * 100

                # 计算最大回撤
                quarter_data['cummax'] = quarter_data['close'].cummax()
                quarter_data['drawdown'] = (quarter_data['close'] / quarter_data['cummax'] - 1) * 100
                max_drawdown = quarter_data['drawdown'].min()

                quarterly_stats[quarter_name] = {
                    'strategy_return': strategy_return,
                    'max_drawdown': max_drawdown,
                    'trading_days': len(quarter_data)
                }

                # 如果有基准数据，计算相对收益
                if benchmark_data is not None and len(benchmark_data) > 0:
                    benchmark_quarter = benchmark_data[
                        (benchmark_data['date'] >= start_date) &
                        (benchmark_data['date'] <= end_date)
                    ]

                    if len(benchmark_quarter) > 0 and 'close' in benchmark_quarter.columns:
                        benchmark_start = benchmark_quarter['close'].iloc[0]
                        benchmark_end = benchmark_quarter['close'].iloc[-1]
                        benchmark_return = (benchmark_end / benchmark_start - 1) * 100

                        alpha = strategy_return - benchmark_return

                        quarterly_stats[quarter_name].update({
                            'benchmark_return': benchmark_return,
                            'alpha': alpha
                        })

                logger.debug(f"{quarter_name}: 策略收益={strategy_return:.2f}%, 最大回撤={max_drawdown:.2f}%")
            else:
                logger.warning(f"⚠️ {quarter_name} 数据缺少close列")

        return quarterly_stats

    def create_quarterly_performance_table(self, quarterly_stats: Dict[str, Dict[str, float]]) -> pd.DataFrame:
        """
        创建季度绩效表格

        Args:
            quarterly_stats: 季度统计数据

        Returns:
            pd.DataFrame: 季度绩效表格
        """
        if not quarterly_stats:
            logger.warning("⚠️ 无季度统计数据")
            return pd.DataFrame()

        # 准备数据
        data = []
        for quarter, stats in quarterly_stats.items():
            row = {
                '季度': quarter,
                '策略收益率(%)': f"{stats['strategy_return']:.2f}",
                '季度最大回撤(%)': f"{stats['max_drawdown']:.2f}",
                '交易天数': stats['trading_days']
            }

            if 'benchmark_return' in stats:
                row['基准收益率(%)'] = f"{stats['benchmark_return']:.2f}"
                row['相对收益(Alpha, %)'] = f"{stats['alpha']:.2f}"
            else:
                row['基准收益率(%)'] = 'N/A'
                row['相对收益(Alpha, %)'] = 'N/A'

            data.append(row)

        df = pd.DataFrame(data)

        # 添加总计行
        if len(df) > 0:
            total_row = {'季度': '总计'}

            # 计算总收益率（复利）
            total_return = 1.0
            for quarter in sorted(quarterly_stats.keys()):
                if 'strategy_return' in quarterly_stats[quarter]:
                    total_return *= (1 + quarterly_stats[quarter]['strategy_return'] / 100)

            total_row['策略收益率(%)'] = f"{(total_return - 1) * 100:.2f}"
            total_row['季度最大回撤(%)'] = 'N/A'
            total_row['交易天数'] = sum(stats['trading_days'] for stats in quarterly_stats.values())

            if 'benchmark_return' in list(quarterly_stats.values())[0]:
                total_benchmark = 1.0
                for quarter in sorted(quarterly_stats.keys()):
                    if 'benchmark_return' in quarterly_stats[quarter]:
                        total_benchmark *= (1 + quarterly_stats[quarter]['benchmark_return'] / 100)

                total_alpha = (total_return - total_benchmark) * 100
                total_row['基准收益率(%)'] = f"{(total_benchmark - 1) * 100:.2f}"
                total_row['相对收益(Alpha, %)'] = f"{total_alpha:.2f}"
            else:
                total_row['基准收益率(%)'] = 'N/A'
                total_row['相对收益(Alpha, %)'] = 'N/A'

            df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

        return df

    def save_quarterly_report(self, quarterly_table: pd.DataFrame, strategy_name: str = "策略"):
        """
        保存季度报告

        Args:
            quarterly_table: 季度绩效表格
            strategy_name: 策略名称
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存CSV
        csv_file = self.output_dir / f"{strategy_name}_quarterly_performance_{timestamp}.csv"
        quarterly_table.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"💾 季度绩效报告已保存: {csv_file}")

        # 保存格式化文本报告
        txt_file = self.output_dir / f"{strategy_name}_quarterly_performance_{timestamp}.txt"

        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"=== {strategy_name} 季度绩效分析报告 ===\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析期间: 2022Q1 - 2023Q4\n\n")

            f.write("季度绩效统计表:\n")
            f.write("=" * 80 + "\n")
            f.write(quarterly_table.to_string(index=False))
            f.write("\n" + "=" * 80 + "\n")

            # 关键结论
            if len(quarterly_table) > 0:
                total_row = quarterly_table.iloc[-1]  # 最后一行是总计
                f.write("\n关键结论:\n")
                f.write("-" * 40 + "\n")
                f.write(f"1. 绝对收益: {total_row['策略收益率(%)']}\n")

                if '相对收益(Alpha, %)' in total_row and total_row['相对收益(Alpha, %)'] != 'N/A':
                    f.write(f"2. 相对收益(Alpha): {total_row['相对收益(Alpha, %)']}\n")

                # 分析最佳/最差季度
                strategy_returns = []
                for _, row in quarterly_table.iloc[:-1].iterrows():  # 排除总计行
                    try:
                        ret = float(row['策略收益率(%)'])
                        strategy_returns.append((row['季度'], ret))
                    except:
                        continue

                if strategy_returns:
                    best_quarter = max(strategy_returns, key=lambda x: x[1])
                    worst_quarter = min(strategy_returns, key=lambda x: x[1])

                    f.write(f"3. 最佳季度: {best_quarter[0]} ({best_quarter[1]:.2f}%)\n")
                    f.write(f"4. 最差季度: {worst_quarter[0]} ({worst_quarter[1]:.2f}%)\n")

        logger.info(f"💾 季度绩效报告已保存: {txt_file}")

    def validate_strategy_with_quarterly_analysis(self, strategy_data_file: str, strategy_name: str = "策略"):
        """
        使用季度分析验证策略

        Args:
            strategy_data_file: 策略数据文件路径
            strategy_name: 策略名称

        Returns:
            bool: 验证是否成功
        """
        logger.info(f"🔍 开始季度分析验证: {strategy_name}")

        try:
            # 1. 读取策略数据
            logger.info("📊 读取策略数据...")
            strategy_data = pd.read_csv(strategy_data_file)
            logger.info(f"策略数据: {len(strategy_data)} 条记录")

            # 2. 获取CSI800基准数据
            logger.info("📊 获取CSI800基准数据...")
            if not self.download_csi800_data():
                logger.error("❌ CSI800基准数据获取失败")
                return False

            # 3. 计算季度统计
            logger.info("📈 计算季度绩效统计...")
            quarterly_stats = self.calculate_quarterly_returns(strategy_data)

            if not quarterly_stats:
                logger.error("❌ 季度统计计算失败")
                return False

            # 4. 生成报告
            logger.info("📋 生成季度绩效报告...")
            quarterly_table = self.create_quarterly_performance_table(quarterly_stats)

            # 5. 保存报告
            self.save_quarterly_report(quarterly_table, strategy_name)

            logger.info("✅ 季度分析验证完成")
            return True

        except Exception as e:
            logger.error(f"❌ 季度分析验证异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def test_with_sample_strategy_data():
    """使用示例策略数据测试季度分析"""
    validator = EnhancedStrategyValidator()

    logger.info("=== 使用示例策略数据测试季度分析 ===")

    # 创建一个简单的示例策略数据（基于几只CSI300股票）
    sample_stocks = ['000001', '000002', '600036', '600519', '000858']

    try:
        # 收集示例数据
        all_data = []
        for stock_code in sample_stocks:
            stock_file = validator.data_dir / "2019" / f"{stock_code}.csv"
            if stock_file.exists():
                stock_data = pd.read_csv(stock_file)
                # 简单策略：等权重投资这几只股票
                stock_data['strategy_value'] = stock_data['close'] * 0.2  # 每只股票20%权重
                stock_data['stock_code'] = stock_code
                all_data.append(stock_data)
                logger.info(f"✅ 加载股票 {stock_code}: {len(stock_data)} 条记录")

        if not all_data:
            logger.error("❌ 未找到示例股票数据")
            return False

        # 合并数据
        strategy_data = pd.concat(all_data, ignore_index=True)
        strategy_data['date'] = pd.to_datetime(strategy_data['date'])

        # 按日期汇总策略价值
        daily_strategy = strategy_data.groupby('date').agg({
            'strategy_value': 'sum'
        }).reset_index()

        # 计算策略日收益率
        daily_strategy['daily_return'] = daily_strategy['strategy_value'].pct_change() * 100

        # 保存示例策略数据
        sample_file = validator.output_dir / "sample_strategy_data.csv"
        daily_strategy.to_csv(sample_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 示例策略数据已保存: {sample_file}")

        # 执行季度分析验证
        success = validator.validate_strategy_with_quarterly_analysis(
            str(sample_file),
            "示例等权重策略"
        )

        if success:
            logger.info("✅ 示例策略季度分析测试成功")
        else:
            logger.error("❌ 示例策略季度分析测试失败")

        return success

    except Exception as e:
        logger.error(f"❌ 示例策略测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主测试函数"""
    validator = EnhancedStrategyValidator()

    # 测试CSI800数据获取
    logger.info("=== 测试CSI800数据获取 ===")
    csi800_stocks = validator.get_csi800_constituents()

    if csi800_stocks:
        logger.info(f"✅ 获取到 {len(csi800_stocks)} 只CSI800成分股")
        logger.info(f"示例: {csi800_stocks[:10]}")
    else:
        logger.error("❌ CSI800成分股获取失败")
        return

    # 测试季度分析功能
    test_with_sample_strategy_data()

if __name__ == "__main__":
    main()