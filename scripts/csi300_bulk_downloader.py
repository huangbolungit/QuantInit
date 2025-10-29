#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300五年数据批量下载器
专为大规模历史数据回测研究设计
"""

import sys
import time
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s',
    handlers=[
        logging.FileHandler('csi300_bulk_download.log', encoding='utf-8'),
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
except ImportError:
    TUSHARE_AVAILABLE = False
    logger.error("Tushare客户端不可用")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("AkShare不可用")


class ProgressTracker:
    """下载进度跟踪器"""

    def __init__(self):
        self.lock = threading.Lock()
        self.total_stocks = 0
        self.completed_stocks = 0
        self.failed_stocks = 0
        self.successful_downloads = {}
        self.failed_downloads = {}
        self.start_time = time.time()

    def set_total(self, total: int):
        """设置总股票数量"""
        with self.lock:
            self.total_stocks = total

    def add_success(self, stock_code: str, record_count: int, source: str):
        """添加成功下载记录"""
        with self.lock:
            self.completed_stocks += 1
            self.successful_downloads[stock_code] = {
                'records': record_count,
                'source': source,
                'timestamp': datetime.now().isoformat()
            }

    def add_failure(self, stock_code: str, error: str):
        """添加失败下载记录"""
        with self.lock:
            self.failed_stocks += 1
            self.failed_downloads[stock_code] = {
                'error': error,
                'timestamp': datetime.now().isoformat()
            }

    def get_progress(self) -> Dict:
        """获取当前进度"""
        with self.lock:
            elapsed = time.time() - self.start_time
            progress_rate = self.completed_stocks / self.total_stocks if self.total_stocks > 0 else 0
            estimated_total = elapsed / progress_rate if progress_rate > 0 else 0
            remaining = estimated_total - elapsed

            return {
                'total': self.total_stocks,
                'completed': self.completed_stocks,
                'failed': self.failed_stocks,
                'progress_rate': progress_rate,
                'elapsed_time': elapsed,
                'estimated_remaining': remaining,
                'success_rate': self.completed_stocks / (self.completed_stocks + self.failed_stocks) if (self.completed_stocks + self.failed_stocks) > 0 else 0
            }

    def save_progress(self, filename: str):
        """保存进度到文件"""
        with self.lock:
            progress_data = {
                'progress': self.get_progress(),
                'successful_downloads': self.successful_downloads,
                'failed_downloads': self.failed_downloads,
                'timestamp': datetime.now().isoformat()
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)


class CSI300BulkDownloader:
    """沪深300批量数据下载器"""

    def __init__(self, primary_source: str = "tushare", data_dir: str = None):
        """
        初始化下载器

        Args:
            primary_source: 首选数据源 ("tushare" 或 "akshare")
            data_dir: 数据存储目录
        """
        self.primary_source = primary_source
        self.data_dir = Path(data_dir) if data_dir else Path("data/historical/stocks/csi300_5year")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录结构
        self.stocks_dir = self.data_dir / "stocks"
        self.meta_dir = self.data_dir / "meta"
        self.reports_dir = self.data_dir / "reports"

        for dir_path in [self.stocks_dir, self.meta_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)

        # 初始化进度跟踪器
        self.progress = ProgressTracker()

        # 下载参数
        self.api_delay = 0.5  # API调用间隔
        self.batch_delay = 60  # 批次间隔
        self.batch_size = 50   # 每批次股票数量
        self.max_workers = 3   # 并发线程数

        # 初始化数据源
        self.data_sources = []
        if TUSHARE_AVAILABLE:
            try:
                self.tushare_client = TushareDataAcquirer(str(self.data_dir))
                self.data_sources.append("tushare")
            except Exception as e:
                logger.warning(f"Tushare初始化失败: {e}")

        if AKSHARE_AVAILABLE:
            self.data_sources.append("akshare")

        logger.info(f"可用数据源: {', '.join(self.data_sources)}")
        logger.info(f"首选数据源: {primary_source}")

    def get_csi300_stocks(self) -> List[str]:
        """获取沪深300成分股列表"""
        logger.info("获取沪深300成分股列表...")

        # 优先使用Tushare获取最新的成分股
        if "tushare" in self.data_sources:
            try:
                stocks = self.tushare_client.get_csi300_stocks()
                if stocks:
                    logger.info(f"从Tushare获取到 {len(stocks)} 只沪深300成分股")
                    # 保存成分股列表
                    with open(self.meta_dir / "csi300_list.json", 'w', encoding='utf-8') as f:
                        json.dump({
                            'source': 'tushare',
                            'stocks': stocks,
                            'count': len(stocks),
                            'timestamp': datetime.now().isoformat()
                        }, f, indent=2, ensure_ascii=False)
                    return stocks
            except Exception as e:
                logger.error(f"从Tushare获取成分股失败: {e}")

        # 备用：使用预定义的沪深300样本
        backup_stocks = self._get_backup_csi300_sample()
        logger.warning(f"使用备用样本股票: {len(backup_stocks)} 只")
        return backup_stocks

    def _get_backup_csi300_sample(self) -> List[str]:
        """获取备用沪深300样本"""
        # 基于沪深300各行业权重的代表性样本
        sample_stocks = [
            # 金融地产 (权重较高)
            '000001', '600000', '600036', '601318', '601398', '000002',
            '600048', '000069', '600016', '601166', '601328', '000651',

            # 主要消费
            '600519', '000858', '000568', '600779', '600887', '000895',
            '002304', '600600', '000596', '000799', '600779', '600597',

            # 医药生物
            '000423', '600276', '000661', '300750', '002007', '002422',
            '000538', '600196', '002038', '300122', '300015', '000999',

            # 科技成长
            '000063', '002415', '300750', '000725', '002230', '300017',
            '000977', '002410', '300144', '000100', '002024', '000988',

            # 周期行业
            '600309', '002648', '000425', '002031', '600031', '000157',
            '002142', '600585', '000630', '601899', '600019', '000709',

            # 稳定增长
            '000069', '600048', '000002', '600048', '000069', '600048',
            '000651', '002415', '000063', '600519', '000858', '600887'
        ]

        # 去重并返回
        return list(set(sample_stocks))

    def download_single_stock(self, stock_code: str, start_date: str, end_date: str) -> bool:
        """下载单只股票数据"""
        logger.debug(f"开始下载 {stock_code}")

        # 按优先级尝试数据源
        sources_order = [self.primary_source]
        for source in self.data_sources:
            if source != self.primary_source:
                sources_order.append(source)

        for source in sources_order:
            try:
                if source == "tushare":
                    df = self.tushare_client.get_stock_daily_data(stock_code, start_date, end_date)
                elif source == "akshare":
                    df = self._download_with_akshare(stock_code, start_date, end_date)
                else:
                    continue

                if not df.empty:
                    # 保存数据
                    success = self._save_stock_data(stock_code, df)
                    if success:
                        self.progress.add_success(stock_code, len(df), source)
                        logger.info(f"[OK] {stock_code} 下载成功: {len(df)} 条记录 (来源: {source})")
                        return True
                    else:
                        logger.error(f"[ERROR] {stock_code} 保存失败")

            except Exception as e:
                logger.error(f"[ERROR] {stock_code} 使用 {source} 下载失败: {e}")
                continue

        # 所有数据源都失败
        self.progress.add_failure(stock_code, "所有数据源都失败")
        logger.error(f"[ERROR] {stock_code} 所有数据源都失败")
        return False

    def _download_with_akshare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用AkShare下载数据"""
        # AkShare需要日期格式转换 YYYY-MM-DD
        start_date_formatted = start_date.replace('-', '')
        end_date_formatted = end_date.replace('-', '')

        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date_formatted,
            end_date=end_date_formatted,
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

    def _save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
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

                # 如果文件存在，合并并去重
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
            logger.error(f"保存 {stock_code} 数据失败: {e}")
            return False

    def download_csi300_bulk(self, start_date: str, end_date: str, max_stocks: int = None):
        """批量下载沪深300数据"""
        logger.info("开始沪深300五年数据批量下载")
        logger.info(f"时间范围: {start_date} 到 {end_date}")
        logger.info(f"数据目录: {self.data_dir}")

        # 获取沪深300成分股
        stock_list = self.get_csi300_stocks()

        if max_stocks:
            stock_list = stock_list[:max_stocks]

        self.progress.set_total(len(stock_list))
        logger.info(f"计划下载 {len(stock_list)} 只股票数据")

        # 分批下载
        total_batches = (len(stock_list) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(stock_list))
            batch_stocks = stock_list[start_idx:end_idx]

            logger.info(f"开始第 {batch_idx + 1}/{total_batches} 批次: {len(batch_stocks)} 只股票")

            # 并发下载当前批次
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.download_single_stock, stock_code, start_date, end_date): stock_code
                    for stock_code in batch_stocks
                }

                for future in as_completed(futures):
                    stock_code = futures[future]
                    try:
                        future.result()
                        time.sleep(self.api_delay)  # API限流
                    except Exception as e:
                        logger.error(f"处理 {stock_code} 时出现异常: {e}")

            # 批次间休息
            if batch_idx < total_batches - 1:
                logger.info(f"批次 {batch_idx + 1} 完成，休息 {self.batch_delay} 秒...")
                time.sleep(self.batch_delay)

            # 保存进度
            self.progress.save_progress(self.meta_dir / f"progress_batch_{batch_idx + 1}.json")

            # 打印当前进度
            progress_info = self.progress.get_progress()
            logger.info(f"当前进度: {progress_info['completed']}/{progress_info['total']} "
                       f"({progress_info['progress_rate']:.1%}) "
                       f"成功率: {progress_info['success_rate']:.1%}")

        # 生成最终报告
        self._generate_final_report()

    def _generate_final_report(self):
        """生成最终下载报告"""
        progress_info = self.progress.get_progress()

        report = {
            'download_summary': {
                'total_stocks': progress_info['total'],
                'successful_downloads': progress_info['completed'],
                'failed_downloads': progress_info['failed'],
                'success_rate': progress_info['success_rate'],
                'total_time_seconds': progress_info['elapsed_time']
            },
            'successful_stocks': self.progress.successful_downloads,
            'failed_stocks': self.progress.failed_downloads,
            'data_sources': self.data_sources,
            'primary_source': self.primary_source,
            'download_config': {
                'api_delay': self.api_delay,
                'batch_size': self.batch_size,
                'max_workers': self.max_workers
            },
            'timestamp': datetime.now().isoformat()
        }

        # 保存报告
        report_file = self.reports_dir / f"csi300_download_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"[COMPLETE] 下载完成! 报告已保存: {report_file}")
        logger.info(f"[SUMMARY] 总计: {progress_info['total']} 只股票")
        logger.info(f"[SUCCESS] 成功: {progress_info['completed']} 只")
        logger.info(f"[FAILED] 失败: {progress_info['failed']} 只")
        logger.info(f"[RATE] 成功率: {progress_info['success_rate']:.1%}")
        logger.info(f"[TIME] 总耗时: {progress_info['elapsed_time']:.1f} 秒")


def main():
    parser = argparse.ArgumentParser(description="沪深300五年数据批量下载器")
    parser.add_argument("--source", choices=["tushare", "akshare"], default="tushare",
                       help="首选数据源")
    parser.add_argument("--start-date", type=str, default="2019-01-01",
                       help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", type=str,
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help="结束日期 YYYY-MM-DD")
    parser.add_argument("--max-stocks", type=int, help="最大下载数量（用于测试）")
    parser.add_argument("--data-dir", type=str, help="数据存储目录")
    parser.add_argument("--test", action="store_true", help="测试模式（下载5只股票）")

    args = parser.parse_args()

    print("沪深300五年数据批量下载器")
    print("=" * 60)

    try:
        # 创建下载器
        downloader = CSI300BulkDownloader(
            primary_source=args.source,
            data_dir=args.data_dir
        )

        # 测试模式
        if args.test:
            max_stocks = 5
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            logger.info("🧪 测试模式: 下载5只股票1年数据")
        else:
            max_stocks = args.max_stocks
            start_date = args.start_date
            end_date = args.end_date

        # 开始批量下载
        downloader.download_csi300_bulk(start_date, end_date, max_stocks)

    except Exception as e:
        logger.error(f"下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()