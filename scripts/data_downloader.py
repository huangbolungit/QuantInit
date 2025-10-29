#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300真实历史数据下载器
解决数据源真实性和样本代表性问题的核心工具
"""

import sys
import time
import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CSI300DataDownloader:
    """沪深300数据下载器"""

    def __init__(self):
        """初始化下载器"""
        self.data_dir = Path("data/historical/stocks")
        self.backup_dir = Path("data/historical/backup")

        # 创建目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 下载参数
        self.api_delay = 0.5  # API调用间隔（秒）
        self.retry_delay = 5   # 重试间隔（秒）
        self.max_retries = 3   # 最大重试次数

        # 统计信息
        self.stats = {
            'total_stocks': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None,
            'failed_stocks': []
        }

    def get_csi300_stocks(self) -> List[str]:
        """获取沪深300成分股列表"""
        try:
            logger.info("正在获取沪深300成分股列表...")

            # 方法1：使用AkShare获取沪深300成分股
            try:
                csi300_df = ak.index_stock_cons(index_code="000300")
                if not csi300_df.empty:
                    stock_codes = csi300_df['品种代码'].tolist()
                    # 确保是6位代码格式
                    stock_codes = [code.zfill(6) for code in stock_codes if code]
                    logger.info(f"成功获取沪深300成分股：{len(stock_codes)}只")
                    return stock_codes
            except Exception as e:
                logger.warning(f"方法1失败: {e}")

            # 方法2：使用备用的获取方式
            try:
                logger.info("尝试备用方法获取成分股...")
                csi300_df = ak.index_zh_a_hist(symbol="000300")
                if not csi300_df.empty:
                    # 从指数成分文件获取
                    cons_df = ak.index_stock_cons(index_code="000300")
                    if not cons_df.empty:
                        stock_codes = cons_df['品种代码'].tolist()
                        stock_codes = [code.zfill(6) for code in stock_codes if code]
                        logger.info(f"备用方法成功：{len(stock_codes)}只")
                        return stock_codes
            except Exception as e:
                logger.warning(f"备用方法失败: {e}")

            # 方法3：使用预定义的沪深300主要成分股（备用）
            logger.warning("使用预定义的沪深300成分股列表...")
            return self._get_predefined_csi300()

        except Exception as e:
            logger.error(f"获取沪深300成分股失败: {e}")
            return self._get_predefined_csi300()

    def _get_predefined_csi300(self) -> List[str]:
        """预定义的沪深300成分股（主要股票）"""
        # 这是一些主要的沪深300成分股，实际使用中应该动态获取
        predefined_stocks = [
            # 金融
            '000001', '000002', '600000', '600036', '600016', '601318', '601398',
            '601166', '601328', '601939', '600015', '601988', '601288',
            # 消费
            '000858', '600519', '000568', '600779', '000596', '002304', '600887',
            # 科技
            '000063', '002415', '300750', '000725', '002230', '300059', '300142',
            # 医药
            '000423', '600276', '000661', '300015', '300003', '300122', '002007',
            # 能源
            '600028', '601857', '600256', '000983', '002202',
            # 工业
            '000425', '600031', '002031', '600150', '000680', '600761',
            # 原材料
            '600309', '002648', '000792', '600160', '000895', '600585',
            # 地产
            '000069', '600048', '001979', '000656', '600340',
            # 公用事业
            '600900', '000883', '600027', '000027'
        ]

        logger.info(f"使用预定义列表：{len(predefined_stocks)}只股票")
        return predefined_stocks

    def download_stock_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        下载单只股票的历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            DataFrame包含OHLCV数据，失败返回None
        """
        for attempt in range(self.max_retries):
            try:
                # AkShare的stock_zh_a_hist函数直接使用6位股票代码，不需要后缀
                symbol = stock_code

                logger.debug(f"尝试下载 {stock_code} - 第{attempt + 1}次尝试")

                # 下载历史数据
                df = ak.stock_zh_a_hist(
                    symbol=symbol,  # 直接使用6位股票代码
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )

                if df.empty:
                    logger.warning(f"股票 {stock_code} 无数据")
                    return None

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
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 添加股票代码
                df['stock_code'] = stock_code

                # 数据质量检查
                df = self._validate_data_quality(df, stock_code)

                if df is not None and not df.empty:
                    logger.debug(f"成功下载 {stock_code}: {len(df)} 条记录")
                    return df
                else:
                    logger.warning(f"股票 {stock_code} 数据质量检查失败")
                    return None

            except Exception as e:
                logger.warning(f"下载 {stock_code} 失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 递增重试延迟
                else:
                    logger.error(f"股票 {stock_code} 下载最终失败")
                    return None

        return None

    def _validate_data_quality(self, df: pd.DataFrame, stock_code: str) -> Optional[pd.DataFrame]:
        """数据质量验证"""
        try:
            # 检查必要列是否存在
            required_columns = ['date', 'open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"股票 {stock_code} 缺少必要列: {missing_columns}")
                return None

            # 检查数据完整性
            null_counts = df.isnull().sum()
            if null_counts['close'] > len(df) * 0.1:  # 超过10%的收盘价缺失
                logger.warning(f"股票 {stock_code} 收盘价缺失过多: {null_counts['close']}")

            # 检查价格合理性
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    # 检查非正价格
                    invalid_prices = (df[col] <= 0).sum()
                    if invalid_prices > 0:
                        logger.warning(f"股票 {stock_code} {col} 列有 {invalid_prices} 个非正价格")
                        df = df[df[col] > 0]  # 移除无效价格

                    # 检查异常高价
                    very_high_prices = (df[col] > 10000).sum()
                    if very_high_prices > 0:
                        logger.warning(f"股票 {stock_code} {col} 列有 {very_high_prices} 个异常高价")

            # 检查价格逻辑（high >= low, close在high和low之间）
            invalid_ohlc = ((df['high'] < df['low']) |
                           (df['close'] > df['high']) |
                           (df['close'] < df['low'])).sum()
            if invalid_ohlc > 0:
                logger.warning(f"股票 {stock_code} 有 {invalid_ohlc} 个价格逻辑错误记录")
                df = df[~((df['high'] < df['low']) |
                       (df['close'] > df['high']) |
                       (df['close'] < df['low']))]

            # 检查成交量
            if 'volume' in df.columns:
                negative_volume = (df['volume'] < 0).sum()
                if negative_volume > 0:
                    logger.warning(f"股票 {stock_code} 有 {negative_volume} 个负成交量记录")
                    df = df[df['volume'] >= 0]

            # 移除重复记录（按日期）
            df = df.drop_duplicates(subset=['date'], keep='last')

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            return df

        except Exception as e:
            logger.error(f"股票 {stock_code} 数据质量验证失败: {e}")
            return None

    def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
        """保存股票数据到CSV文件"""
        try:
            # 按年份分目录存储
            df['year'] = df['date'].dt.year

            for year, year_data in df.groupby('year'):
                year_dir = self.data_dir / str(year)
                year_dir.mkdir(exist_ok=True)

                filename = year_dir / f"{stock_code}.csv"
                year_data = year_data.drop('year', axis=1)

                # 如果文件已存在，进行增量更新
                if filename.exists():
                    existing_df = pd.read_csv(filename)
                    existing_df['date'] = pd.to_datetime(existing_df['date'])

                    # 合并数据，去重
                    combined_df = pd.concat([existing_df, year_data], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                    combined_df = combined_df.sort_values('date')

                    combined_df.to_csv(filename, index=False)
                    logger.debug(f"更新 {stock_code} {year}年数据: {len(year_data)} 条新记录")
                else:
                    year_data.to_csv(filename, index=False)
                    logger.debug(f"创建 {stock_code} {year}年数据文件: {len(year_data)} 条记录")

            return True

        except Exception as e:
            logger.error(f"保存股票 {stock_code} 数据失败: {e}")
            return False

    def download_csi300_data(self, years: int = 5, resume: bool = False) -> Dict:
        """
        下载沪深300所有成分股的历史数据

        Args:
            years: 下载年数
            resume: 是否恢复中断的下载
        """
        self.stats['start_time'] = datetime.now()

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        logger.info(f"开始下载沪深300数据")
        logger.info(f"时间范围: {start_date_str} 到 {end_date_str}")
        logger.info(f"预计年数: {years}")

        # 获取沪深300成分股
        stock_codes = self.get_csi300_stocks()

        if not stock_codes:
            logger.error("无法获取沪深300成分股列表")
            return self.stats

        self.stats['total_stocks'] = len(stock_codes)
        logger.info(f"总共需要下载 {len(stock_codes)} 只股票")

        # 如果是恢复模式，检查已下载的股票
        downloaded_stocks = set()
        if resume:
            downloaded_stocks = self._get_downloaded_stocks()
            logger.info(f"恢复模式：已下载 {len(downloaded_stocks)} 只股票")

        # 下载股票数据
        for i, stock_code in enumerate(stock_codes, 1):
            # 跳过已下载的股票（恢复模式）
            if resume and stock_code in downloaded_stocks:
                logger.info(f"跳过已下载: {stock_code} ({i}/{len(stock_codes)})")
                self.stats['successful'] += 1
                continue

            logger.info(f"下载进度: {i}/{len(stock_codes)} - {stock_code}")

            try:
                # 下载数据
                df = self.download_stock_data(stock_code, start_date_str, end_date_str)

                if df is not None and not df.empty:
                    # 保存数据
                    if self.save_stock_data(stock_code, df):
                        self.stats['successful'] += 1
                    else:
                        self.stats['failed'] += 1
                        self.stats['failed_stocks'].append(stock_code)
                else:
                    self.stats['failed'] += 1
                    self.stats['failed_stocks'].append(stock_code)

            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时发生错误: {e}")
                self.stats['failed'] += 1
                self.stats['failed_stocks'].append(stock_code)

            # API延迟，避免触发限制
            time.sleep(self.api_delay)

            # 每10只股票输出一次进度
            if i % 10 == 0:
                success_rate = self.stats['successful'] / i * 100
                logger.info(f"当前进度: {i}/{len(stock_codes)}, 成功率: {success_rate:.1f}%")

        self.stats['end_time'] = datetime.now()

        # 保存下载统计信息
        self._save_download_stats()

        # 生成下载报告
        self._generate_download_report()

        return self.stats

    def _get_downloaded_stocks(self) -> set:
        """获取已下载的股票代码"""
        downloaded_stocks = set()
        try:
            for year_dir in self.data_dir.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for csv_file in year_dir.glob("*.csv"):
                        stock_code = csv_file.stem
                        downloaded_stocks.add(stock_code)
        except Exception as e:
            logger.warning(f"获取已下载股票列表失败: {e}")

        return downloaded_stocks

    def _save_download_stats(self):
        """保存下载统计信息"""
        try:
            stats_file = self.data_dir / "download_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                # 转换datetime对象为字符串
                stats_copy = self.stats.copy()
                if 'start_time' in stats_copy:
                    stats_copy['start_time'] = stats_copy['start_time'].isoformat()
                if 'end_time' in stats_copy:
                    stats_copy['end_time'] = stats_copy['end_time'].isoformat()

                json.dump(stats_copy, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存下载统计失败: {e}")

    def _generate_download_report(self):
        """生成下载报告"""
        try:
            duration = self.stats['end_time'] - self.stats['start_time']
            success_rate = self.stats['successful'] / self.stats['total_stocks'] * 100

            report = f"""
沪深300数据下载报告
=====================

下载时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
耗时: {duration}

统计信息:
- 目标股票数: {self.stats['total_stocks']}
- 成功下载: {self.stats['successful']}
- 下载失败: {self.stats['failed']}
- 成功率: {success_rate:.1f}%

数据质量:
- 数据格式: 前复权日线数据
- 包含字段: 日期、开盘、收盘、最高、最低、成交量、成交额
- 质量检查: 价格合理性、逻辑一致性、完整性验证

存储位置:
- 主目录: {self.data_dir}
- 按年份分组: {self.data_dir}/2024/, {self.data_dir}/2023/, 等
- 统计文件: {self.data_dir}/download_stats.json

失败股票:
{chr(10).join(f"- {stock}" for stock in self.stats['failed_stocks']) if self.stats['failed_stocks'] else "无"}

使用建议:
1. 数据下载完成后，可以运行回测测试
2. 建议定期更新数据（每周一次）
3. 如果失败率较高，可以尝试重新下载失败的股票
            """

            report_file = self.data_dir / "download_report.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"下载报告已保存到: {report_file}")

        except Exception as e:
            logger.error(f"生成下载报告失败: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="沪深300历史数据下载器")
    parser.add_argument("--years", type=int, default=5, help="下载年数，默认5年")
    parser.add_argument("--resume", action="store_true", help="恢复中断的下载")
    parser.add_argument("--stocks", type=str, help="指定股票代码列表，逗号分隔（用于测试）")

    args = parser.parse_args()

    logger.info("沪深300数据下载器启动")
    logger.info("=" * 50)

    downloader = CSI300DataDownloader()

    if args.stocks:
        # 测试模式：下载指定股票
        stock_codes = [s.strip() for s in args.stocks.split(",")]
        logger.info(f"测试模式：下载指定股票 {stock_codes}")

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime('%Y%m%d')

        for stock_code in stock_codes:
            logger.info(f"下载 {stock_code}")
            df = downloader.download_stock_data(stock_code, start_date, end_date)
            if df is not None:
                downloader.save_stock_data(stock_code, df)
                logger.info(f"成功下载 {stock_code}")
            else:
                logger.error(f"下载失败 {stock_code}")

            time.sleep(downloader.api_delay)
    else:
        # 正式模式：下载沪深300
        stats = downloader.download_csi300_data(years=args.years, resume=args.resume)

        logger.info("=" * 50)
        logger.info("下载完成!")
        logger.info(f"成功率: {stats['successful']}/{stats['total_stocks']} ({stats['successful']/stats['total_stocks']*100:.1f}%)")

        if stats['failed'] > 0:
            logger.warning(f"失败股票: {stats['failed']} 只")
            logger.info(f"可以使用 --resume 参数恢复下载")


if __name__ == "__main__":
    main()