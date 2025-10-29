#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化数据质量验证脚本
验证沪深300股票数据的完整性和质量
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging
import json

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDataValidator:
    """简化的数据质量验证器"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path("data/historical/stocks/csi300_5year")
        self.stocks_dir = self.data_dir / "stocks"
        self.reports_dir = self.data_dir / "reports"

        # 创建报告目录
        self.reports_dir.mkdir(exist_ok=True)

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
            missing_values = df.isnull().sum().sum()

            # 价格数据合理性检查
            price_issues = 0
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    price_issues += (df[col] <= 0).sum()
                    price_issues += (df[col] > 10000).sum()

            # 计算质量分数
            quality_score = 1.0
            quality_score -= (price_issues / total_records) * 0.3
            quality_score -= (missing_values / (total_records * len(df.columns))) * 0.2
            quality_score = max(0, min(1, quality_score))

            # 计算收益率统计
            return_stats = {}
            if 'close' in df.columns and len(df) > 1:
                df['daily_return'] = df['close'].pct_change()
                return_stats = {
                    'mean_daily_return': round(df['daily_return'].mean(), 6),
                    'std_daily_return': round(df['daily_return'].std(), 6),
                    'max_return': round(df['daily_return'].max(), 6),
                    'min_return': round(df['daily_return'].min(), 6)
                }

            return {
                'stock_code': stock_code,
                'status': 'valid',
                'total_records': total_records,
                'date_range': date_range,
                'missing_values': missing_values,
                'price_issues': price_issues,
                'quality_score': round(quality_score, 3),
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
                'avg_quality_score': round(np.mean(quality_scores), 3),
                'min_quality_score': round(np.min(quality_scores), 3),
                'max_quality_score': round(np.max(quality_scores), 3),
                'avg_records_per_stock': round(np.mean(total_records), 0),
                'total_records_all_stocks': int(np.sum(total_records)),
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
        logger.info(f"平均质量分数: {summary_stats['avg_quality_score']}")

        return report


def main():
    print("沪深300股票数据质量验证")
    print("=" * 50)

    try:
        # 创建验证器
        validator = SimpleDataValidator()

        # 运行验证
        report = validator.validate_all_stocks()

        # 打印简要结果
        summary = report['summary']
        print(f"\n📊 数据质量验证结果:")
        print(f"总股票数: {summary['total_stocks']}")
        print(f"有效股票: {summary['valid_stocks']}")
        print(f"无效股票: {summary['invalid_stocks']}")
        print(f"平均质量分数: {summary['avg_quality_score']}")
        print(f"平均每只股票记录数: {summary['avg_records_per_stock']:.0f}")

        if 'quality_distribution' in summary:
            print(f"\n📈 质量分布:")
            for level, count in summary['quality_distribution'].items():
                print(f"  {level}: {count} 只")

        # 显示一些优质股票示例
        valid_stocks = {k: v for k, v in report['individual_stocks'].items() if v['status'] == 'valid'}
        if valid_stocks:
            # 按质量分数排序
            sorted_stocks = sorted(valid_stocks.items(), key=lambda x: x[1]['quality_score'], reverse=True)
            print(f"\n🏆 质量最高的5只股票:")
            for i, (stock_code, data) in enumerate(sorted_stocks[:5], 1):
                print(f"  {i}. {stock_code}: 质量分数 {data['quality_score']}, 记录数 {data['total_records']}, "
                      f"时间范围 {data['date_range']['start']} 到 {data['date_range']['end']}")

    except Exception as e:
        logger.error(f"数据质量验证失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())