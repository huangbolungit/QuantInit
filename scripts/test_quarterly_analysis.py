#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试季度分析功能 - 使用已下载的CSI300数据演示季度分析
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.enhanced_strategy_validation import EnhancedStrategyValidator

def create_sample_strategy_data():
    """创建示例策略数据用于测试"""
    # 使用CSI300前10只股票的数据作为示例策略数据
    data_dir = Path("backend/data/historical/stocks")

    # 找到第一个年份目录
    year_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir() and "csi300" in d.name])

    if not year_dirs:
        logger.error("❌ 未找到CSI300数据目录")
        return None

    first_year_dir = year_dirs[0]
    stocks_dir = first_year_dir / "stocks"

    # 读取前10只股票数据
    sample_data = []
    for csv_file in sorted(stocks_dir.glob("*.csv"))[:10]:
        try:
            df = pd.read_csv(csv_file)
            df['date'] = pd.to_datetime(df['date'])
            df['stock_code'] = csv_file.stem
            sample_data.append(df)
        except Exception as e:
            logger.warning(f"读取文件 {csv_file} 失败: {e}")

    if not sample_data:
        logger.error("❌ 无可用的策略数据")
        return None

    # 合并所有数据
    strategy_data = pd.concat(sample_data, ignore_index=True)
    strategy_data = strategy_data.sort_values(['stock_code', 'date']).reset_index(drop=True)

    logger.info(f"✅ 创建示例策略数据: {len(strategy_data)} 条记录, {strategy_data['stock_code'].nunique()} 只股票")
    return strategy_data

def test_quarterly_analysis():
    """测试季度分析功能"""
    logger.info("🧪 开始测试季度分析功能...")

    # 创建示例策略数据
    logger.info("📊 创建示例策略数据...")
    strategy_data = create_sample_strategy_data()

    if strategy_data is None:
        logger.error("❌ 无法创建策略数据")
        return False

    # 创建验证器
    validator = EnhancedStrategyValidator()

    # 测试季度统计计算
    logger.info("📈 测试季度统计计算...")
    quarterly_stats = validator.calculate_quarterly_returns(strategy_data)

    if not quarterly_stats:
        logger.error("❌ 季度统计计算失败")
        return False

    # 创建季度表格
    logger.info("📋 创建季度绩效表格...")
    quarterly_table = validator.create_quarterly_performance_table(quarterly_stats)

    logger.info("✅ 季度分析测试完成!")
    logger.info(f"📊 季度绩效表格:")
    print(quarterly_table)

    # 保存结果
    validator.save_quarterly_report(quarterly_table, "测试策略")

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    test_quarterly_analysis()