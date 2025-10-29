#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Yahoo Finance客户端 - 专门解决限速问题
实现智能请求间隔控制和批量数据获取
"""

import yfinance as yf
import pandas as pd
import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EnhancedYahooFinanceClient:
    """增强版Yahoo Finance客户端，专门解决限速问题"""

    def __init__(self):
        self.session_timeout = 30
        self.request_history = []
        self.max_requests_per_minute = 10  # 保守估计
        self.max_requests_per_hour = 100  # 保守估计
        self.base_delay = 2.0  # 基础延迟2秒
        self.max_delay = 30.0  # 最大延迟30秒
        self.backoff_factor = 1.5  # 退避因子

    def _calculate_smart_delay(self, attempt_count: int = 0) -> float:
        """计算智能延迟时间"""
        # 指数退避 + 随机抖动
        base_delay = self.base_delay * (self.backoff_factor ** attempt_count)
        random_jitter = random.uniform(0.5, 1.5)
        delay = min(base_delay * random_jitter, self.max_delay)

        logger.debug(f"Calculated delay: {delay:.2f}s (attempt: {attempt_count})")
        return delay

    def _check_rate_limit(self) -> bool:
        """检查当前是否超过速率限制"""
        now = datetime.now()

        # 清理过期的请求记录
        self.request_history = [
            req_time for req_time in self.request_history
            if now - req_time < timedelta(hours=1)
        ]

        # 检查分钟级别限制
        recent_minute = [
            req_time for req_time in self.request_history
            if now - req_time < timedelta(minutes=1)
        ]

        if len(recent_minute) >= self.max_requests_per_minute:
            logger.warning(f"Minute rate limit reached: {len(recent_minute)}/{self.max_requests_per_minute}")
            return False

        # 检查小时级别限制
        if len(self.request_history) >= self.max_requests_per_hour:
            logger.warning(f"Hour rate limit reached: {len(self.request_history)}/{self.max_requests_per_hour}")
            return False

        return True

    def _wait_for_rate_limit(self) -> None:
        """等待直到可以发送请求"""
        while not self._check_rate_limit():
            wait_time = self._calculate_smart_delay(1)
            logger.info(f"Rate limit reached, waiting {wait_time:.2f}s...")
            time.sleep(wait_time)

    def _record_request(self) -> None:
        """记录请求时间"""
        self.request_history.append(datetime.now())

    def _download_with_retry(self, ticker, start_date, end_date, max_attempts: int = 3) -> Optional[pd.DataFrame]:
        """带重试机制的数据下载"""
        for attempt in range(max_attempts):
            try:
                # 等待速率限制
                self._wait_for_rate_limit()

                # 记录请求
                self._record_request()

                # 下载数据
                logger.debug(f"Downloading {ticker} (attempt {attempt + 1})")
                data = ticker.history(start=start_date, end=end_date)

                if len(data) > 0:
                    logger.info(f"Successfully downloaded {len(data)} records for {ticker}")
                    return data
                else:
                    logger.warning(f"No data returned for {ticker}")
                    return None

            except Exception as e:
                error_msg = str(e).lower()

                if "too many requests" in error_msg or "rate limited" in error_msg:
                    logger.warning(f"Rate limit hit for {ticker} (attempt {attempt + 1}): {e}")
                    if attempt < max_attempts - 1:
                        delay = self._calculate_smart_delay(attempt + 1)
                        logger.info(f"Backing off for {delay:.2f}s...")
                        time.sleep(delay)
                    continue
                else:
                    logger.error(f"Error downloading {ticker}: {e}")
                    if attempt < max_attempts - 1:
                        delay = self._calculate_smart_delay(attempt + 1)
                        logger.info(f"Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    continue

        logger.error(f"Failed to download {ticker} after {max_attempts} attempts")
        return None

    def download_single_stock(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """下载单只股票数据"""
        try:
            ticker = yf.Ticker(symbol)
            return self._download_with_retry(ticker, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to create ticker for {symbol}: {e}")
            return None

    def download_multiple_stocks_batch(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """批量下载多只股票数据（优化的批处理）"""
        results = {}
        failed_symbols = []

        logger.info(f"Starting batch download of {len(symbols)} symbols")
        logger.info(f"Date range: {start_date} to {end_date}")

        for i, symbol in enumerate(symbols):
            logger.info(f"Processing {symbol} ({i+1}/{len(symbols)})")

            try:
                # 创建新的ticker实例（避免会话复用问题）
                ticker = yf.Ticker(symbol)
                data = self._download_with_retry(ticker, start_date, end_date)

                if data is not None and len(data) > 0:
                    # 标准化数据格式
                    data = self._standardize_data(data, symbol)
                    results[symbol] = data
                    logger.info(f"✅ Successfully processed {symbol}: {len(data)} records")
                else:
                    failed_symbols.append(symbol)
                    logger.warning(f"❌ No data for {symbol}")

            except Exception as e:
                failed_symbols.append(symbol)
                logger.error(f"❌ Error processing {symbol}: {e}")

        # 输出统计信息
        success_count = len(results)
        total_count = len(symbols)
        success_rate = success_count / total_count * 100 if total_count > 0 else 0

        logger.info(f"Batch download completed:")
        logger.info(f"  Success: {success_count}/{total_count} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {len(failed_symbols)}")

        if failed_symbols:
            logger.warning(f"Failed symbols: {failed_symbols}")

        return results

    def _standardize_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """标准化数据格式以匹配我们的标准"""
        # 重命名列名以匹配标准格式
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }

        data = data.rename(columns=column_mapping)

        # 重置索引并添加日期列
        data = data.reset_index()
        data = data.rename(columns={'Date': 'date'})

        # 确保日期格式正确
        data['date'] = pd.to_datetime(data['date'])

        # 添加股票代码
        data['symbol'] = symbol

        # 选择需要的列（按我们的标准格式）
        standard_columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        if 'adj_close' in data.columns:
            standard_columns.append('adj_close')

        # 按日期排序
        data = data.sort_values('date').reset_index(drop=True)

        return data[standard_columns]

    def test_connectivity(self, test_symbol: str = "000001.SS") -> bool:
        """测试Yahoo Finance连接性"""
        try:
            logger.info(f"Testing Yahoo Finance connectivity with {test_symbol}")
            ticker = yf.Ticker(test_symbol)

            # 尝试获取最近一天的数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            data = ticker.history(start=start_date, end=end_date)

            if len(data) > 0:
                logger.info(f"✅ Yahoo Finance connectivity test successful")
                logger.info(f"   Got {len(data)} records for {test_symbol}")
                logger.info(f"   Date range: {data.index.min().date()} to {data.index.max().date()}")
                return True
            else:
                logger.warning("⚠️ Yahoo Finance connectivity test: no data returned")
                return False

        except Exception as e:
            logger.error(f"❌ Yahoo Finance connectivity test failed: {e}")
            return False

    def get_optimal_batch_size(self, total_symbols: int) -> int:
        """根据速率限制计算最优批量大小"""
        # 保守策略：每批最多5个股票，每个股票间隔2秒
        # 这样每批大约需要10秒，在速率限制范围内
        max_batch_size = 5

        # 如果股票数量很少，可以适当增加批量大小
        if total_symbols <= 10:
            max_batch_size = 3
        elif total_symbols <= 20:
            max_batch_size = 4

        logger.info(f"Optimal batch size for {total_symbols} symbols: {max_batch_size}")
        return max_batch_size

    def download_with_progressive_batches(self, symbols: List[str], start_date: str, end_date: str,
                                        batch_size: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """使用渐进式批量下载"""
        if batch_size is None:
            batch_size = self.get_optimal_batch_size(len(symbols))

        all_results = {}
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        logger.info(f"Starting progressive batch download:")
        logger.info(f"  Total symbols: {len(symbols)}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Total batches: {total_batches}")

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]

            logger.info(f"\n--- Processing Batch {batch_num + 1}/{total_batches} ---")
            logger.info(f"Symbols: {batch_symbols}")

            # 批量下载
            batch_results = self.download_multiple_stocks_batch(batch_symbols, start_date, end_date)
            all_results.update(batch_results)

            # 批次间延迟
            if batch_num < total_batches - 1:  # 不是最后一批
                inter_batch_delay = self._calculate_smart_delay(0) * 2  # 双倍基础延迟
                logger.info(f"Waiting {inter_batch_delay:.2f}s before next batch...")
                time.sleep(inter_batch_delay)

        # 最终统计
        final_success = len(all_results)
        final_total = len(symbols)
        final_success_rate = final_success / final_total * 100 if final_total > 0 else 0

        logger.info(f"\n=== Progressive Batch Download Summary ===")
        logger.info(f"Total symbols: {final_total}")
        logger.info(f"Successful: {final_success}")
        logger.info(f"Success rate: {final_success_rate:.1f}%")

        return all_results


def main():
    """测试函数"""
    client = EnhancedYahooFinanceClient()

    # 测试连接性
    if not client.test_connectivity():
        logger.error("Cannot proceed: Yahoo Finance connectivity test failed")
        return

    # 测试批量下载
    test_symbols = ["000001.SS", "600519.SS", "000002.SS"]
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    logger.info(f"\nTesting batch download with {len(test_symbols)} symbols")
    results = client.download_with_progressive_batches(test_symbols, start_date, end_date)

    for symbol, data in results.items():
        logger.info(f"{symbol}: {len(data)} records from {data['date'].min()} to {data['date'].max()}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()