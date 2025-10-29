#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将分层的股票数据结构扁平化
从 year/stock.csv 合并为 stock.csv
"""

import pandas as pd
import shutil
from pathlib import Path
from typing import Dict, List
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataFlattener:
    """数据结构扁平化器"""

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据扁平化器初始化: {self.source_dir} -> {self.target_dir}")

    def flatten_single_stock(self, stock_code: str) -> bool:
        """扁平化单只股票的数据"""
        try:
            all_data = []

            # 查找所有年份的数据文件
            for year_file in self.source_dir.rglob(f"{stock_code}.csv"):
                if year_file.is_file():
                    try:
                        df = pd.read_csv(year_file)
                        df['date'] = pd.to_datetime(df['date'])
                        all_data.append(df)
                        logger.debug(f"读取 {year_file}: {len(df)} 条记录")
                    except Exception as e:
                        logger.warning(f"读取 {year_file} 失败: {e}")

            if not all_data:
                logger.warning(f"未找到股票 {stock_code} 的数据")
                return False

            # 合并所有数据
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'], keep='last')

            # 确保股票代码格式正确（6位数字）
            if '股票代码' in combined_df.columns:
                combined_df['股票代码'] = combined_df['股票代码'].astype(str).str.zfill(6)
            if 'stock_code' in combined_df.columns:
                combined_df['stock_code'] = combined_df['stock_code'].astype(str).str.zfill(6)

            # 保存到目标目录
            target_file = self.target_dir / f"{stock_code}.csv"
            combined_df.to_csv(target_file, index=False)

            logger.info(f"[OK] {stock_code}: {len(combined_df)} 条记录 -> {target_file}")
            return True

        except Exception as e:
            logger.error(f"扁平化 {stock_code} 失败: {e}")
            return False

    def flatten_all_stocks(self):
        """扁平化所有股票数据"""
        logger.info("开始扁平化所有股票数据...")

        # 获取所有股票代码
        stock_codes = set()
        for file_path in self.source_dir.rglob("*.csv"):
            if file_path.is_file():
                stock_code = file_path.stem
                if stock_code.isdigit() and len(stock_code) == 6:
                    stock_codes.add(stock_code)

        stock_codes = sorted(list(stock_codes))
        logger.info(f"发现 {len(stock_codes)} 只股票")

        success_count = 0
        for i, stock_code in enumerate(stock_codes, 1):
            if i % 10 == 0:
                logger.info(f"处理进度: {i}/{len(stock_codes)}")

            if self.flatten_single_stock(stock_code):
                success_count += 1

        logger.info(f"扁平化完成: {success_count}/{len(stock_codes)} 只股票成功")

        # 生成报告
        report = {
            'total_stocks': len(stock_codes),
            'successful_stocks': success_count,
            'failed_stocks': len(stock_codes) - success_count,
            'source_directory': str(self.source_dir),
            'target_directory': str(self.target_dir)
        }

        # 验证结果
        target_files = list(self.target_dir.glob("*.csv"))
        logger.info(f"目标目录文件数: {len(target_files)}")

        # 统计数据覆盖
        if target_files:
            sample_file = target_files[0]
            sample_df = pd.read_csv(sample_file)
            date_range = {
                'start': sample_df['date'].min(),
                'end': sample_df['date'].max(),
                'records': len(sample_df)
            }
            logger.info(f"样本数据 ({sample_file.stem}): {date_range}")

        return report


def main():
    print("股票数据结构扁平化工具")
    print("=" * 40)

    # 设置路径
    source_dir = "data/historical/stocks/csi300_5year/stocks"
    target_dir = "data/historical/stocks/csi300_flat"

    try:
        # 创建扁平化器
        flattener = DataFlattener(source_dir, target_dir)

        # 执行扁平化
        report = flattener.flatten_all_stocks()

        print(f"\n扁平化结果:")
        print(f"总股票数: {report['total_stocks']}")
        print(f"成功: {report['successful_stocks']}")
        print(f"失败: {report['failed_stocks']}")

    except Exception as e:
        logger.error(f"扁平化失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())