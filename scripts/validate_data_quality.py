#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量验证脚本
验证沪深300股票数据的完整性和质量
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import json
import matplotlib.pyplot as plt
import seaborn as sns

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class DataQualityValidator:
    """数据质量验证器"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path("data/historical/stocks/csi300_5year")
        self.stocks_dir = self.data_dir / "stocks"
        self.reports_dir = self.data_dir / "reports"
        self.plots_dir = self.data_dir / "plots"

        # 创建报告和图表目录
        for dir_path in [self.reports_dir, self.plots_dir]:
            dir_path.mkdir(exist_ok=True)

        logger.info(f"数据质量验证器初始化完成，数据目录: {self.data_dir}")

    def load_stock_data(self, stock_code: str) -> pd.DataFrame:
        """加载单只股票的所有年份数据"""
        all_data = []

        # 遍历所有年份目录
        for year_dir in sorted(self.stocks_dir.iterdir()):
            if year_dir.is_dir() and year_dir.name.isdigit():
                file_path = year_dir / f"{stock_code}.csv"
                if file_path.exists():
                    try:
                        df = pd.read_csv(file_path)
                        df['date'] = pd.to_datetime(df['date'])
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"读取 {file_path} 失败: {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'], keep='last')
            return combined_df
        else:
            return pd.DataFrame()

    def validate_single_stock(self, stock_code: str) -> Dict[str, Any]:
        """验证单只股票的数据质量"""
        try:
            df = self.load_stock_data(stock_code)

            if df.empty:
                return {
                    'stock_code': stock_code,
                    'status': 'no_data',
                    'total_records': 0,
                    'date_range': None,
                    'missing_values': {},
                    'quality_score': 0.0
                }

            # 基本统计
            total_records = len(df)
            date_range = {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d'),
                'trading_days': total_records
            }

            # 缺失值检查
            missing_values = df.isnull().sum().to_dict()

            # 价格数据合理性检查
            price_issues = 0
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    price_issues += (df[col] <= 0).sum()
                    price_issues += (df[col] > 10000).sum()  # 异常高价

            # 成交量检查
            volume_issues = 0
            if 'volume' in df.columns:
                volume_issues += (df['volume'] < 0).sum()

            # 数据连续性检查
            df_sorted = df.sort_values('date')
            df_sorted['date_diff'] = df_sorted['date'].diff().dt.days
            large_gaps = (df_sorted['date_diff'] > 15).sum()  # 超过15天的间隔

            # 计算质量分数
            quality_score = 1.0
            quality_score -= (price_issues / total_records) * 0.3
            quality_score -= (large_gaps / total_records) * 0.2
            quality_score -= (df.isnull().sum().sum() / (total_records * len(df.columns))) * 0.3
            quality_score -= (volume_issues / total_records) * 0.2

            # 检查必要列是否存在
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                quality_score -= len(missing_columns) * 0.1

            quality_score = max(0, min(1, quality_score))

            # 计算收益率统计
            if 'close' in df.columns and len(df) > 1:
                df['daily_return'] = df['close'].pct_change()
                return_stats = {
                    'mean_daily_return': df['daily_return'].mean(),
                    'std_daily_return': df['daily_return'].std(),
                    'max_return': df['daily_return'].max(),
                    'min_return': df['daily_return'].min(),
                    'skewness': df['daily_return'].skew(),
                    'kurtosis': df['daily_return'].kurtosis()
                }
            else:
                return_stats = {}

            return {
                'stock_code': stock_code,
                'status': 'valid',
                'total_records': total_records,
                'date_range': date_range,
                'missing_values': {k: v for k, v in missing_values.items() if v > 0},
                'price_issues': price_issues,
                'volume_issues': volume_issues,
                'data_gaps': large_gaps,
                'missing_columns': missing_columns,
                'quality_score': quality_score,
                'return_statistics': return_stats
            }

        except Exception as e:
            logger.error(f"验证 {stock_code} 时出错: {e}")
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'quality_score': 0.0
            }

    def validate_all_stocks(self) -> Dict[str, Any]:
        """验证所有股票数据质量"""
        logger.info("开始验证所有股票数据质量...")

        # 获取所有股票代码
        stock_files = list(self.stocks_dir.rglob("*.csv"))
        stock_codes = set()
        for file_path in stock_files:
            stock_code = file_path.stem
            if stock_code.isdigit() and len(stock_code) == 6:
                stock_codes.add(stock_code)

        stock_codes = sorted(list(stock_codes))
        logger.info(f"发现 {len(stock_codes)} 只股票的数据")

        validation_results = {}
        quality_scores = []
        total_records = []

        for i, stock_code in enumerate(stock_codes, 1):
            if i % 10 == 0:
                logger.info(f"验证进度: {i}/{len(stock_codes)}")

            result = self.validate_single_stock(stock_code)
            validation_results[stock_code] = result

            if result['status'] == 'valid':
                quality_scores.append(result['quality_score'])
                total_records.append(result['total_records'])

        # 生成汇总统计
        if quality_scores:
            summary_stats = {
                'total_stocks': len(stock_codes),
                'valid_stocks': len([r for r in validation_results.values() if r['status'] == 'valid']),
                'invalid_stocks': len([r for r in validation_results.values() if r['status'] != 'valid']),
                'avg_quality_score': np.mean(quality_scores),
                'min_quality_score': np.min(quality_scores),
                'max_quality_score': np.max(quality_scores),
                'avg_records_per_stock': np.mean(total_records),
                'total_records_all_stocks': np.sum(total_records),
                'quality_distribution': {
                    'excellent (>0.9)': len([s for s in quality_scores if s > 0.9]),
                    'good (0.7-0.9)': len([s for s in quality_scores if 0.7 <= s <= 0.9]),
                    'fair (0.5-0.7)': len([s for s in quality_scores if 0.5 <= s < 0.7]),
                    'poor (<0.5)': len([s for s in quality_scores if s < 0.5])
                }
            }
        else:
            summary_stats = {
                'total_stocks': len(stock_codes),
                'valid_stocks': 0,
                'invalid_stocks': len(stock_codes),
                'avg_quality_score': 0,
                'message': 'No valid data found'
            }

        report = {
            'summary': summary_stats,
            'individual_stocks': validation_results,
            'validation_timestamp': datetime.now().isoformat()
        }

        # 保存报告
        report_file = self.reports_dir / f"data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"数据质量验证完成，报告已保存: {report_file}")
        logger.info(f"总计: {summary_stats['total_stocks']} 只股票")
        logger.info(f"有效: {summary_stats['valid_stocks']} 只")
        logger.info(f"平均质量分数: {summary_stats['avg_quality_score']:.3f}")

        return report

    def create_quality_plots(self, report: Dict[str, Any]):
        """创建数据质量可视化图表"""
        logger.info("生成数据质量可视化图表...")

        individual_stocks = report['individual_stocks']
        valid_stocks = {k: v for k, v in individual_stocks.items() if v['status'] == 'valid'}

        if not valid_stocks:
            logger.warning("没有有效数据，无法生成图表")
            return

        # 提取数据
        stock_codes = list(valid_stocks.keys())
        quality_scores = [valid_stocks[code]['quality_score'] for code in stock_codes]
        total_records = [valid_stocks[code]['total_records'] for code in stock_codes]

        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('沪深300股票数据质量分析', fontsize=16, fontweight='bold')

        # 1. 质量分数分布直方图
        axes[0, 0].hist(quality_scores, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('质量分数分布')
        axes[0, 0].set_xlabel('质量分数')
        axes[0, 0].set_ylabel('股票数量')
        axes[0, 0].axvline(np.mean(quality_scores), color='red', linestyle='--', label=f'平均值: {np.mean(quality_scores):.3f}')
        axes[0, 0].legend()

        # 2. 记录数量分布
        axes[0, 1].hist(total_records, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
        axes[0, 1].set_title('交易记录数量分布')
        axes[0, 1].set_xlabel('记录数量')
        axes[0, 1].set_ylabel('股票数量')
        axes[0, 1].axvline(np.mean(total_records), color='red', linestyle='--', label=f'平均值: {np.mean(total_records):.0f}')
        axes[0, 1].legend()

        # 3. 质量分数 vs 记录数量散点图
        axes[1, 0].scatter(total_records, quality_scores, alpha=0.6, color='purple')
        axes[1, 0].set_title('质量分数 vs 记录数量')
        axes[1, 0].set_xlabel('记录数量')
        axes[1, 0].set_ylabel('质量分数')

        # 添加趋势线
        z = np.polyfit(total_records, quality_scores, 1)
        p = np.poly1d(z)
        axes[1, 0].plot(total_records, p(total_records), "r--", alpha=0.8)

        # 4. 质量等级饼图
        quality_dist = report['summary']['quality_distribution']
        labels = list(quality_dist.keys())
        sizes = list(quality_dist.values())
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']

        axes[1, 1].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[1, 1].set_title('数据质量等级分布')

        plt.tight_layout()
        plot_file = self.plots_dir / f"data_quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"质量分析图表已保存: {plot_file}")


def main():
    print("沪深300股票数据质量验证")
    print("=" * 50)

    try:
        # 创建验证器
        validator = DataQualityValidator()

        # 运行验证
        report = validator.validate_all_stocks()

        # 生成图表
        validator.create_quality_plots(report)

        # 打印简要结果
        summary = report['summary']
        print(f"\n📊 数据质量验证结果:")
        print(f"总股票数: {summary['total_stocks']}")
        print(f"有效股票: {summary['valid_stocks']}")
        print(f"无效股票: {summary['invalid_stocks']}")
        print(f"平均质量分数: {summary['avg_quality_score']:.3f}")
        print(f"平均每只股票记录数: {summary['avg_records_per_stock']:.0f}")

        if 'quality_distribution' in summary:
            print(f"\n📈 质量分布:")
            for level, count in summary['quality_distribution'].items():
                print(f"  {level}: {count} 只")

    except Exception as e:
        logger.error(f"数据质量验证失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())