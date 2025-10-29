#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据获取客户端 - 负责历史数据采集和本地存储
"""

import tushare as ts
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

# 加载环境变量
load_dotenv()

class TushareDataAcquirer:
    """Tushare数据获取器"""

    def __init__(self, data_dir: str = None, token: str = None):
        """
        初始化数据获取器

        Args:
            data_dir: 数据存储目录，默认为项目根目录下的data目录
            token: Tushare API token，如果不提供则从环境变量TUSHARE_TOKEN读取
        """
        # 获取Tushare token
        self.token = token or os.getenv('TUSHARE_TOKEN')
        if not self.token:
            raise ValueError("请提供Tushare token或设置环境变量TUSHARE_TOKEN")

        # 初始化Tushare接口
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        # 设置数据目录
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data" / "historical"
        else:
            self.data_dir = Path(data_dir)

        # 创建子目录
        self.stocks_dir = self.data_dir / "stocks"
        self.sectors_dir = self.data_dir / "sectors"
        self.fundamentals_dir = self.data_dir / "fundamentals"
        self.index_dir = self.data_dir / "index"

        for dir_path in [self.stocks_dir, self.sectors_dir, self.fundamentals_dir, self.index_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        print(f"Tushare数据存储目录: {self.data_dir}")
        print(f"API初始化完成，Token: {self.token[:10]}...")

    def get_csi300_stocks(self) -> List[str]:
        """获取沪深300成分股股票代码"""
        try:
            print("获取沪深300成分股...")
            # 获取最新的沪深300成分股
            df = self.pro.index_consistent(index_code='000300.SH')

            if df.empty:
                print("未获取到沪深300成分股数据")
                return []

            # 提取股票代码并转换格式
            stock_codes = []
            for code in df['con_code']:
                # 转换格式：例如 000001.SZ -> 000001
                clean_code = code.split('.')[0]
                stock_codes.append(clean_code)

            print(f"获取到 {len(stock_codes)} 只沪深300成分股")
            return stock_codes

        except Exception as e:
            print(f"获取沪深300成分股失败: {e}")
            return []

    def get_stock_basic_info(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """获取股票基本信息"""
        try:
            print("获取股票基本信息...")
            # 获取所有股票基本信息
            df = self.pro.stock_basic(exchange='', list_status='L',
                                     fields='ts_code,symbol,name,area,industry,market,list_date')

            if df.empty:
                print("未获取到股票基本信息")
                return pd.DataFrame()

            # 如果指定了股票代码，则过滤
            if stock_codes:
                df = df[df['symbol'].isin(stock_codes)]

            # 保存基本信息
            basic_file = self.data_dir / "stock_basic.csv"
            df.to_csv(basic_file, index=False, encoding='utf-8-sig')
            print(f"股票基本信息已保存: {basic_file}")

            return df

        except Exception as e:
            print(f"获取股票基本信息失败: {e}")
            return pd.DataFrame()

    def get_stock_daily_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取单只股票的日线数据

        Args:
            stock_code: 股票代码（不带后缀，如 000001）
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            DataFrame包含OHLCV数据
        """
        try:
            # 转换股票代码格式：000001 -> 000001.SZ 或 000001.SH
            # 需要先获取基本信息来确定交易所
            basic_info = self.get_stock_basic_info([stock_code])
            if basic_info.empty:
                print(f"未找到股票 {stock_code} 的基本信息")
                return pd.DataFrame()

            ts_code = basic_info.iloc[0]['ts_code']  # 例如 000001.SZ

            # 获取历史数据
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df.empty:
                print(f"股票 {stock_code} 无数据")
                return pd.DataFrame()

            # 标准化列名
            df = df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'vol': 'volume',
                'amount': 'amount'
            })

            # 重新排列列顺序
            df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]

            # 确保数据类型正确
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            for col in ['open', 'close', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

            # 添加股票代码
            df['stock_code'] = stock_code

            # 按日期排序（升序）
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

    def download_csi300_data(self, start_date: str, end_date: str, max_stocks: int = None):
        """
        下载沪深300成分股的历史数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            max_stocks: 最大下载数量，用于测试
        """
        print(f"开始下载沪深300历史数据: {start_date} 到 {end_date}")

        # 获取沪深300成分股
        stock_codes = self.get_csi300_stocks()

        if not stock_codes:
            print("未获取到沪深300成分股，尝试使用备用股票列表")
            stock_codes = [
                '000001', '000002', '000858', '000895', '002415',
                '600000', '600036', '600519', '600887', '601318'
            ]

        if max_stocks:
            stock_codes = stock_codes[:max_stocks]

        # 获取基本信息
        self.get_stock_basic_info(stock_codes)

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
                        print(f"  {stock_code} 下载成功: {len(df)} 条记录")
                    else:
                        error_count += 1
                        print(f"  {stock_code} 保存失败")
                else:
                    error_count += 1
                    print(f"  {stock_code} 无数据")

                # API限流控制（Tushare每分钟限制调用次数）
                time.sleep(0.2)

            except Exception as e:
                print(f"处理股票 {stock_code} 时出错: {e}")
                error_count += 1

            # 每处理50只股票输出一次进度
            if i % 50 == 0:
                print(f"当前进度: {i}/{total_stocks}, 成功: {success_count}, 失败: {error_count}")

        print(f"下载完成! 总计: {total_stocks}, 成功: {success_count}, 失败: {error_count}")

    def download_sample_data(self, days: int = 365):
        """下载样本数据用于测试"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        print(f"下载沪深300样本数据: {start_date} 到 {end_date}")
        self.download_csi300_data(start_date, end_date, max_stocks=20)

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
    try:
        # 检查是否设置了Tushare token
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            print("错误: 请设置环境变量 TUSHARE_TOKEN")
            print("获取方法: https://tushare.pro/document/1?doc_id=109")
            return

        acquirer = TushareDataAcquirer()

        # 下载样本数据
        acquirer.download_sample_data(days=90)

        # 验证数据质量
        test_stock = '000001'
        quality = acquirer.validate_data_quality(test_stock)
        print(f"股票 {test_stock} 数据质量: {quality}")

    except Exception as e:
        print(f"运行失败: {e}")


if __name__ == "__main__":
    main()