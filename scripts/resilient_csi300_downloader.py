#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳健的沪深300成分股下载器
针对网络问题优化，支持小批次和重试机制
"""

import sys
import time
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import logging
import json

# 设置环境变量
from dotenv import load_dotenv
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csi300_resilient_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# 导入数据源客户端
try:
    from app.services.data_acquisition.tushare_client import TushareDataAcquirer
    TUSHARE_AVAILABLE = True
    logger.info("Tushare客户端可用")
except ImportError:
    TUSHARE_AVAILABLE = False
    logger.error("Tushare客户端不可用")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AkShare客户端可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("AkShare客户端不可用")


class ResilientDownloader:
    """稳健的数据下载器"""

    def __init__(self):
        self.tushare_client = None
        self.data_dir = Path("data/historical/stocks/csi300_5year")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化Tushare客户端
        if TUSHARE_AVAILABLE:
            tushare_token = os.getenv('TUSHARE_TOKEN')
            if tushare_token:
                try:
                    self.tushare_client = TushareDataAcquirer(tushare_token)
                    logger.info("Tushare客户端初始化成功")
                except Exception as e:
                    logger.error(f"Tushare客户端初始化失败: {e}")
            else:
                logger.warning("未找到Tushare token")

    def load_csi300_list(self) -> pd.DataFrame:
        """加载沪深300成分股列表"""
        try:
            if os.path.exists('csi300_full_list.csv'):
                logger.info("从本地文件加载沪深300列表")
                return pd.read_csv('csi300_full_list.csv', encoding='utf-8')
            else:
                logger.info("从AkShare获取沪深300列表")
                csi300_stocks = ak.index_stock_cons(symbol='000300')
                csi300_stocks.to_csv('csi300_full_list.csv', index=False, encoding='utf-8')
                return csi300_stocks
        except Exception as e:
            logger.error(f"获取沪深300列表失败: {e}")
            return pd.DataFrame()

    def load_existing_stocks(self) -> Set[str]:
        """加载已存在的股票数据"""
        existing_stocks = set()
        try:
            for csv_file in self.data_dir.rglob("*.csv"):
                stock_code = csv_file.stem
                if len(stock_code) == 6 and stock_code.isdigit():
                    existing_stocks.add(stock_code)
            logger.info(f"找到已存在的股票数据: {len(existing_stocks)} 只")
        except Exception as e:
            logger.error(f"加载已存在股票数据失败: {e}")

        return existing_stocks

    def download_stock_tushare(self, stock_code: str, start_date: str, end_date: str) -> bool:
        """使用Tushare下载单只股票数据"""
        if not self.tushare_client:
            return False

        try:
            # 获取股票数据
            df = self.tushare_client.get_stock_daily_data(stock_code, start_date, end_date)
            if df is not None and not df.empty:
                # 保存数据
                self._save_stock_data(df, stock_code)
                logger.info(f"[Tushare] {stock_code} 下载成功: {len(df)} 条记录")
                return True
            else:
                logger.warning(f"[Tushare] {stock_code} 未获取到数据")
                return False
        except Exception as e:
            logger.error(f"[Tushare] {stock_code} 下载失败: {e}")
            return False

    def download_stock_akshare(self, stock_code: str, start_date: str, end_date: str) -> bool:
        """使用AkShare下载单只股票数据"""
        if not AKSHARE_AVAILABLE:
            return False

        try:
            # 尝试下载，增加重试机制
            for attempt in range(3):
                try:
                    # 使用股票代码获取数据
                    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                          start_date=start_date.replace('-', ''),
                                          end_date=end_date.replace('-', ''), adjust="qfq")

                    if df is not None and not df.empty:
                        # 标准化列名
                        df = self._standardize_columns(df)
                        # 保存数据
                        self._save_stock_data(df, stock_code)
                        logger.info(f"[AkShare] {stock_code} 下载成功: {len(df)} 条记录 (尝试 {attempt + 1})")
                        return True
                    else:
                        logger.warning(f"[AkShare] {stock_code} 未获取到数据 (尝试 {attempt + 1})")

                except Exception as e:
                    logger.warning(f"[AkShare] {stock_code} 第 {attempt + 1} 次尝试失败: {e}")
                    if attempt < 2:  # 不是最后一次尝试
                        time.sleep(2 ** attempt)  # 指数退避

            logger.error(f"[AkShare] {stock_code} 所有尝试均失败")
            return False

        except Exception as e:
            logger.error(f"[AkShare] {stock_code} 下载失败: {e}")
            return False

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        try:
            # AkShare返回的列名映射
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            }

            df = df.rename(columns=column_mapping)

            # 确保必要的列存在
            required_columns = ['date', 'open', 'close', 'high', 'low', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"缺少必要列: {col}")

            # 添加股票代码列
            df['stock_code'] = df.iloc[0].get('股票代码', '')

            return df

        except Exception as e:
            logger.error(f"列名标准化失败: {e}")
            return df

    def _save_stock_data(self, df: pd.DataFrame, stock_code: str):
        """保存股票数据到年份文件夹"""
        try:
            # 确保日期列是datetime类型
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

                # 按年份分组保存
                for year, year_data in df.groupby(df['date'].dt.year):
                    year_dir = self.data_dir / "stocks" / str(year)
                    year_dir.mkdir(parents=True, exist_ok=True)

                    file_path = year_dir / f"{stock_code}.csv"
                    year_data.to_csv(file_path, index=False, encoding='utf-8')

            else:
                logger.warning(f"数据中没有日期列，无法按年份保存: {stock_code}")

        except Exception as e:
            logger.error(f"保存数据失败 {stock_code}: {e}")

    def download_batch(self, stock_codes: List[str], start_date: str, end_date: str,
                      batch_size: int = 10) -> Dict[str, bool]:
        """下载一批股票数据"""
        results = {}

        logger.info(f"开始下载批次: {len(stock_codes)} 只股票")

        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            logger.info(f"处理小批次 {i//batch_size + 1}: {batch}")

            for stock_code in batch:
                success = False

                # 优先使用Tushare
                if self.tushare_client:
                    success = self.download_stock_tushare(stock_code, start_date, end_date)

                # 如果Tushare失败，尝试AkShare
                if not success:
                    success = self.download_stock_akshare(stock_code, start_date, end_date)

                results[stock_code] = success

                # 添加延迟避免频率限制
                time.sleep(0.5)

            # 批次间延迟
            if i + batch_size < len(stock_codes):
                logger.info(f"批次间休息 2 秒...")
                time.sleep(2)

        return results

    def download_missing_stocks(self, batch_size: int = 20, max_stocks: int = None):
        """下载缺失的股票数据"""
        logger.info("开始稳健下载缺失的沪深300成分股...")

        # 加载沪深300列表
        csi300_df = self.load_csi300_list()
        if csi300_df.empty:
            logger.error("无法获取沪深300成分股列表")
            return

        # 获取所有成分股代码
        all_stocks = set(csi300_df['品种代码'].astype(str).str.zfill(6))

        # 获取已存在的股票
        existing_stocks = self.load_existing_stocks()

        # 找出缺失的股票
        missing_stocks = list(all_stocks - existing_stocks)

        if max_stocks:
            missing_stocks = missing_stocks[:max_stocks]

        logger.info(f"总成分股: {len(all_stocks)} 只")
        logger.info(f"已下载: {len(existing_stocks)} 只")
        logger.info(f"需要下载: {len(missing_stocks)} 只")

        if not missing_stocks:
            logger.info("所有股票数据已完整，无需下载")
            return

        # 下载参数
        start_date = "2020-01-01"
        end_date = "2024-12-31"

        # 开始下载
        successful = {}
        failed = {}

        results = self.download_batch(missing_stocks, start_date, end_date, batch_size)

        for stock_code, success in results.items():
            if success:
                successful[stock_code] = True
            else:
                failed[stock_code] = True

        # 输出结果
        logger.info("=" * 50)
        logger.info("下载完成统计:")
        logger.info(f"成功: {len(successful)} 只")
        logger.info(f"失败: {len(failed)} 只")
        logger.info(f"成功率: {len(successful)/(len(successful)+len(failed))*100:.1f}%")

        if failed:
            logger.warning(f"失败的股票: {list(failed.keys())}")

        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="稳健的沪深300数据下载器")
    parser.add_argument("--batch-size", type=int, default=20, help="批次大小")
    parser.add_argument("--max-stocks", type=int, help="最大下载数量")
    parser.add_argument("--start-date", type=str, default="2020-01-01", help="开始日期")
    parser.add_argument("--end-date", type=str, default="2024-12-31", help="结束日期")

    args = parser.parse_args()

    downloader = ResilientDownloader()
    downloader.download_missing_stocks(args.batch_size, args.max_stocks)


if __name__ == "__main__":
    import argparse
    main()