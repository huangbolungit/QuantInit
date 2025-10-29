#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare数据获取客户端 - 负责历史数据采集和本地存储
"""

import akshare as ak
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import sys
import os

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

class AkShareDataAcquirer:
    """AkShare数据获取器"""

    def __init__(self, data_dir: str = None):
        """
        初始化数据获取器

        Args:
            data_dir: 数据存储目录，默认为项目根目录下的data目录
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent.parent / "data" / "historical"
        else:
            self.data_dir = Path(data_dir)

        # 创建子目录
        self.stocks_dir = self.data_dir / "stocks"
        self.sectors_dir = self.data_dir / "sectors"
        self.fundamentals_dir = self.data_dir / "fundamentals"

        for dir_path in [self.stocks_dir, self.sectors_dir, self.fundamentals_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        print(f"数据存储目录: {self.data_dir}")

    def get_all_stock_codes(self) -> List[str]:
        """获取所有A股股票代码"""
        try:
            print("获取A股股票列表...")
            # 获取A股实时行情数据
            stock_df = ak.stock_zh_a_spot_em()

            # 提取股票代码
            stock_codes = stock_df['代码'].tolist()

            # 过滤掉ST股票和退市股票
            stock_codes = [code for code in stock_codes if not code.startswith('ST')]

            print(f"共获取到 {len(stock_codes)} 只股票")
            return stock_codes

        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []

    def get_stock_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取单只股票的日线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            DataFrame包含OHLCV数据
        """
        try:
            # 格式化股票代码
            if len(stock_code) == 6:
                formatted_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
            else:
                formatted_code = stock_code

            # 获取历史数据
            df = ak.stock_zh_a_hist(symbol=formatted_code, period="daily",
                                  start_date=start_date, end_date=end_date, adjust="qfq")

            if df.empty:
                print(f"股票 {stock_code} 无数据")
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })

            # 确保数据类型正确
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'close', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            # 添加股票代码
            df['stock_code'] = stock_code

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"获取股票 {stock_code} 数据失败: {e}")
            return pd.DataFrame()

    def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
        """保存股票数据到CSV文件"""
        try:
            if df.empty:
                return False

            # 按年份分目录存储
            df['year'] = df['date'].dt.year

            for year, year_data in df.groupby('year'):
                year_dir = self.stocks_dir / str(year)
                year_dir.mkdir(exist_ok=True)

                filename = year_dir / f"{stock_code}.csv"
                year_data = year_data.drop('year', axis=1)

                # 如果文件存在，追加数据；否则创建新文件
                if filename.exists():
                    existing_df = pd.read_csv(filename)
                    existing_df['date'] = pd.to_datetime(existing_df['date'])
                    combined_df = pd.concat([existing_df, year_data], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                    combined_df = combined_df.sort_values('date')
                    combined_df.to_csv(filename, index=False)
                else:
                    year_data.to_csv(filename, index=False)

            return True

        except Exception as e:
            print(f"保存股票 {stock_code} 数据失败: {e}")
            return False

    def get_shenwan_sector_classification(self) -> Dict[str, str]:
        """获取申万行业分类"""
        try:
            print("获取申万行业分类...")
            # 获取申万行业分类 - 使用正确的API
            sector_df = ak.index_sw_spot_cons()

            sector_mapping = {}
            for _, row in sector_df.iterrows():
                sector_code = row['指数代码']
                sector_name = row['指数名称']
                stock_codes = row['成分代码']

                if isinstance(stock_codes, str):
                    for stock_code in stock_codes.split(','):
                        sector_mapping[stock_code] = sector_name

            # 保存行业分类数据
            sector_file = self.sectors_dir / "shenwan_classification.csv"
            sector_series = pd.Series(sector_mapping)
            sector_df = pd.DataFrame({
                'stock_code': sector_series.index,
                'sector_name': sector_series.values
            })
            sector_df.to_csv(sector_file, index=False)

            print(f"获取到 {len(sector_mapping)} 只股票的行业分类")
            return sector_mapping

        except Exception as e:
            print(f"获取行业分类失败: {e}")
            # 尝试备用方法
            return self._get_sector_classification_backup()

    def _get_sector_classification_backup(self) -> Dict[str, str]:
        """备用行业分类获取方法"""
        try:
            print("使用备用方法获取行业分类...")
            # 简化的行业分类映射
            sector_mapping = {}

            # 一些主要的申万行业分类
            major_sectors = {
                '银行': ['000001', '600000', '600036', '601318', '601398', '601939'],
                '地产': ['000002', '600048', '000069', '600340', '001979'],
                '白酒': ['000858', '600519', '000568', '600779', '000596'],
                '医药': ['000423', '600276', '000661', '300015', '300003'],
                '科技': ['000063', '002415', '300750', '600036', '000725'],
                '新能源': ['300750', '002594', '300274', '002460', '600884'],
                '化工': ['600309', '002648', '000792', '600160', '000425'],
                '机械': ['000425', '002031', '600150', '000680', '600761']
            }

            for sector, stocks in major_sectors.items():
                for stock in stocks:
                    sector_mapping[stock] = sector

            print(f"备用方法获取到 {len(sector_mapping)} 只股票的行业分类")
            return sector_mapping

        except Exception as e:
            print(f"备用方法也失败: {e}")
            return {}

    def download_all_stock_data(self, start_date: str, end_date: str, max_stocks: int = None):
        """
        下载所有股票的历史数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            max_stocks: 最大下载数量，用于测试
        """
        print(f"开始下载历史数据: {start_date} 到 {end_date}")

        # 获取股票列表
        stock_codes = self.get_all_stock_codes()

        if max_stocks:
            stock_codes = stock_codes[:max_stocks]

        total_stocks = len(stock_codes)
        success_count = 0
        error_count = 0

        for i, stock_code in enumerate(stock_codes, 1):
            print(f"进度: {i}/{total_stocks} - 正在下载 {stock_code}")

            try:
                # 获取股票数据
                df = self.get_stock_daily_data(stock_code, start_date, end_date)

                if not df.empty:
                    # 保存数据
                    if self.save_stock_data(stock_code, df):
                        success_count += 1
                    else:
                        error_count += 1
                else:
                    error_count += 1

                # 避免请求过于频繁
                time.sleep(0.1)

            except Exception as e:
                print(f"处理股票 {stock_code} 时出错: {e}")
                error_count += 1

            # 每处理100只股票输出一次进度
            if i % 100 == 0:
                print(f"当前进度: {i}/{total_stocks}, 成功: {success_count}, 失败: {error_count}")

        print(f"下载完成! 总计: {total_stocks}, 成功: {success_count}, 失败: {error_count}")

    def download_sample_data(self, days: int = 365):
        """下载样本数据用于测试"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        print(f"下载样本数据: {start_date} 到 {end_date}")

        # 下载一些知名股票的数据用于测试
        sample_stocks = [
            '000001',  # 平安银行
            '000002',  # 万科A
            '000858',  # 五粮液
            '600000',  # 浦发银行
            '600036',  # 招商银行
            '600519',  # 贵州茅台
            '600887',  # 伊利股份
            '000858',  # 五粮液
        ]

        self.download_all_stock_data(start_date, end_date, max_stocks=len(sample_stocks))

    def validate_data_quality(self, stock_code: str) -> Dict[str, Any]:
        """验证数据质量"""
        try:
            # 查找该股票的所有数据文件
            stock_files = list(self.stocks_dir.rglob(f"{stock_code}.csv"))

            if not stock_files:
                return {"valid": False, "error": "未找到数据文件"}

            all_data = []
            for file_path in stock_files:
                df = pd.read_csv(file_path)
                df['date'] = pd.to_datetime(df['date'])
                all_data.append(df)

            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values('date').drop_duplicates(subset=['date'])

            # 数据质量检查
            total_records = len(combined_df)
            null_values = combined_df.isnull().sum().to_dict()
            date_range = {
                "start": combined_df['date'].min().strftime('%Y-%m-%d'),
                "end": combined_df['date'].max().strftime('%Y-%m-%d')
            }

            # 检查价格数据合理性
            price_issues = 0
            for col in ['open', 'high', 'low', 'close']:
                if col in combined_df.columns:
                    # 检查负价格
                    price_issues += (combined_df[col] <= 0).sum()
                    # 检查异常高价
                    price_issues += (combined_df[col] > 10000).sum()

            return {
                "valid": price_issues == 0 and total_records > 0,
                "total_records": total_records,
                "date_range": date_range,
                "null_values": null_values,
                "price_issues": price_issues,
                "files_count": len(stock_files)
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}


def main():
    """主函数 - 用于测试"""
    acquirer = AkShareDataAcquirer()

    # 下载样本数据
    acquirer.download_sample_data(days=30)

    # 获取行业分类
    sector_mapping = acquirer.get_shenwan_sector_classification()

    # 验证数据质量
    test_stock = '000001'
    quality = acquirer.validate_data_quality(test_stock)
    print(f"股票 {test_stock} 数据质量: {quality}")


if __name__ == "__main__":
    main()