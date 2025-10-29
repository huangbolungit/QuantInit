#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳健数据下载器 - 支持AkShare和Tushare双数据源
自动切换数据源，确保数据获取的稳定性
"""

import sys
import time
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robust_data_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# 尝试导入数据源
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AkShare 可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AkShare 不可用")

try:
    import tushare as ts
    from dotenv import load_dotenv
    import os
    TUSHARE_AVAILABLE = True
    logger.info("Tushare 可用")
except ImportError:
    TUSHARE_AVAILABLE = False
    logger.warning("Tushare 不可用")


class RobustDataDownloader:
    """稳健数据下载器 - 支持多数据源自动切换"""

    def __init__(self, primary_source: str = "akshare", data_dir: str = None):
        """
        初始化下载器

        Args:
            primary_source: 首选数据源 ("akshare" 或 "tushare")
            data_dir: 数据存储目录
        """
        self.primary_source = primary_source
        self.data_dir = Path(data_dir) if data_dir else Path("data/historical/stocks")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据源
        self.data_sources = []

        if AKSHARE_AVAILABLE:
            self.data_sources.append("akshare")
        if TUSHARE_AVAILABLE and os.getenv('TUSHARE_TOKEN'):
            self.data_sources.append("tushare")

        if not self.data_sources:
            raise RuntimeError("没有可用的数据源！请安装 AkShare 或配置 Tushare token")

        logger.info(f"可用数据源: {', '.join(self.data_sources)}")
        logger.info(f"首选数据源: {primary_source}")

        # 下载参数
        self.api_delay = 0.5
        self.retry_delay = 5
        self.max_retries = 3

        # 统计信息
        self.stats = {
            'total_stocks': 0,
            'successful': 0,
            'failed': 0,
            'source_success': {source: 0 for source in self.data_sources}
        }

    def get_stock_data_akshare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用AkShare获取股票数据"""
        try:
            # AkShare直接使用6位股票代码
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if df.empty:
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
            logger.error(f"AkShare获取{stock_code}失败: {e}")
            return pd.DataFrame()

    def get_stock_data_tushare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用Tushare获取股票数据"""
        try:
            # 初始化Tushare
            load_dotenv()
            token = os.getenv('TUSHARE_TOKEN')
            if not token:
                logger.error("未配置Tushare token")
                return pd.DataFrame()

            ts.set_token(token)
            pro = ts.pro_api()

            # 获取股票基本信息确定交易所
            basic_info = pro.stock_basic(exchange='', list_status='L',
                                        fields='ts_code,symbol,name,area,industry,market,list_date')
            stock_row = basic_info[basic_info['symbol'] == stock_code]

            if stock_row.empty:
                logger.error(f"未找到股票{stock_code}的基本信息")
                return pd.DataFrame()

            ts_code = stock_row.iloc[0]['ts_code']

            # 获取历史数据
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df.empty:
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

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"Tushare获取{stock_code}失败: {e}")
            return pd.DataFrame()

    def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票数据，自动切换数据源

        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame包含股票数据
        """
        # 确定数据源尝试顺序
        sources_order = [self.primary_source]
        for source in self.data_sources:
            if source != self.primary_source:
                sources_order.append(source)

        for source in sources_order:
            try:
                logger.info(f"尝试使用 {source} 获取 {stock_code} 数据")

                if source == "akshare":
                    df = self.get_stock_data_akshare(stock_code, start_date, end_date)
                elif source == "tushare":
                    df = self.get_stock_data_tushare(stock_code, start_date, end_date)
                else:
                    continue

                if not df.empty:
                    logger.info(f"{source} 成功获取 {stock_code}: {len(df)} 条记录")
                    self.stats['source_success'][source] += 1
                    return df
                else:
                    logger.warning(f"{source} 返回空数据")

            except Exception as e:
                logger.error(f"{source} 获取 {stock_code} 失败: {e}")

        logger.error(f"所有数据源都无法获取 {stock_code} 数据")
        return pd.DataFrame()

    def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
        """保存股票数据到CSV文件"""
        try:
            if df.empty:
                return False

            # 按年份分目录存储
            df['year'] = df['date'].dt.year

            for year, year_data in df.groupby('year'):
                year_dir = self.data_dir / str(year)
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
            logger.error(f"保存股票 {stock_code} 数据失败: {e}")
            return False

    def download_stocks(self, stock_codes: List[str], start_date: str, end_date: str, max_stocks: int = None):
        """
        下载多只股票数据

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            max_stocks: 最大下载数量（用于测试）
        """
        if max_stocks:
            stock_codes = stock_codes[:max_stocks]

        self.stats['total_stocks'] = len(stock_codes)
        logger.info(f"开始下载 {len(stock_codes)} 只股票数据")
        logger.info(f"时间范围: {start_date} 到 {end_date}")
        logger.info(f"首选数据源: {self.primary_source}")

        for i, stock_code in enumerate(stock_codes, 1):
            logger.info(f"进度: {i}/{len(stock_codes)} - {stock_code}")

            try:
                # 获取股票数据
                df = self.get_stock_data(stock_code, start_date, end_date)

                if not df.empty:
                    # 保存数据
                    if self.save_stock_data(stock_code, df):
                        self.stats['successful'] += 1
                        logger.info(f"  {stock_code} 保存成功: {len(df)} 条记录")
                    else:
                        self.stats['failed'] += 1
                        logger.error(f"  {stock_code} 保存失败")
                else:
                    self.stats['failed'] += 1
                    logger.warning(f"  {stock_code} 无数据")

                # API限流控制
                time.sleep(self.api_delay)

            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {e}")
                self.stats['failed'] += 1

            # 每处理50只股票输出一次进度
            if i % 50 == 0:
                success_rate = self.stats['successful'] / i * 100
                logger.info(f"当前进度: {i}/{len(stock_codes)}, 成功率: {success_rate:.1f}%")

        # 输出最终统计
        self.print_stats()

    def print_stats(self):
        """输出统计信息"""
        logger.info("=" * 50)
        logger.info("下载完成统计:")
        logger.info(f"总计股票: {self.stats['total_stocks']}")
        logger.info(f"成功下载: {self.stats['successful']}")
        logger.info(f"下载失败: {self.stats['failed']}")
        logger.info(f"成功率: {self.stats['successful']/self.stats['total_stocks']*100:.1f}%")

        logger.info("各数据源成功次数:")
        for source, count in self.stats['source_success'].items():
            logger.info(f"  {source}: {count}")

    def get_csi300_sample(self, max_stocks: int = 50) -> List[str]:
        """获取沪深300样本股票代码"""
        # 沪深300代表性样本（包含各行业龙头）
        csi300_sample = [
            # 银行
            '000001',  # 平安银行
            '600000',  # 浦发银行
            '600036',  # 招商银行
            '601318',  # 中国平安
            '601398',  # 工商银行

            # 地产
            '000002',  # 万科A
            '000069',  # 华侨城A
            '600048',  # 保利发展

            # 白酒
            '000568',  # 泸州老窖
            '000858',  # 五粮液
            '600519',  # 贵州茅台
            '600779',  # 水井坊
            '000596',  # 古井贡酒

            # 医药
            '000423',  # 东阿阿胶
            '600276',  # 恒瑞医药
            '000661',  # 长春高新

            # 科技
            '000063',  # 中兴通讯
            '002415',  # 海康威视
            '300750',  # 宁德时代
            '000725',  # 京东方A

            # 新能源
            '002594',  # 比亚迪
            '300274',  # 阳光电源
            '002460',  # 赣锋锂业
            '600884',  # 杉杉股份

            # 化工
            '600309',  # 万华化学
            '002648',  # 卫星石化

            # 机械
            '000425',  # 徐工机械
            '002031',  # 巨轮智能

            # 消费
            '600887',  # 伊利股份
            '000895',  # 双汇发展
        ]

        return csi300_sample[:max_stocks]


def main():
    parser = argparse.ArgumentParser(description="稳健数据下载器")
    parser.add_argument("--source", choices=["akshare", "tushare"], default="akshare",
                       help="首选数据源")
    parser.add_argument("--mode", choices=["sample", "custom"], default="sample",
                       help="下载模式")
    parser.add_argument("--days", type=int, default=365,
                       help="样本数据天数")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYYMMDD")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYYMMDD")
    parser.add_argument("--max-stocks", type=int, help="最大下载数量")
    parser.add_argument("--data-dir", type=str, help="数据存储目录")
    parser.add_argument("--stocks", type=str, help="指定股票代码，逗号分隔")

    args = parser.parse_args()

    print("A股智能投顾助手 - 稳健数据下载器")
    print("=" * 50)

    try:
        # 创建下载器
        downloader = RobustDataDownloader(
            primary_source=args.source,
            data_dir=args.data_dir
        )

        # 确定日期范围
        if not args.start_date or not args.end_date:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y%m%d')
        else:
            start_date = args.start_date
            end_date = args.end_date

        # 确定股票列表
        if args.mode == "sample":
            stock_codes = downloader.get_csi300_sample(args.max_stocks or 20)
        else:  # custom
            if not args.stocks:
                print("错误: custom模式需要指定股票代码")
                sys.exit(1)
            stock_codes = [s.strip() for s in args.stocks.split(",")]

        # 开始下载
        downloader.download_stocks(stock_codes, start_date, end_date, args.max_stocks)

    except Exception as e:
        logger.error(f"下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()