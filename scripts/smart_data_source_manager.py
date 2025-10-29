#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据源管理器 - 解决多数据源限速问题的统一解决方案
"""

import os
import sys
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.data_acquisition.akshare_client import AkShareDataAcquirer
from backend.app.services.data_acquisition.tushare_client import TushareDataAcquirer
from backend.app.services.data_acquisition.yahoo_finance_client_enhanced import EnhancedYahooFinanceClient
from backend.app.services.data_acquisition.baostock_client import BaoStockClient

logger = logging.getLogger(__name__)


class SmartDataSourceManager:
    """智能数据源管理器 - 自动切换和优化数据获取"""

    def __init__(self):
        self.data_sources = {}

        # 尝试初始化各个数据源，BaoStock优先
        try:
            self.data_sources['baostock'] = BaoStockClient()
            logger.info("✅ BaoStock client initialized")
        except Exception as e:
            logger.warning(f"❌ Failed to initialize BaoStock client: {e}")

        try:
            self.data_sources['yahoo'] = EnhancedYahooFinanceClient()
            logger.info("✅ Yahoo Finance client initialized")
        except Exception as e:
            logger.warning(f"❌ Failed to initialize Yahoo Finance client: {e}")

        try:
            self.data_sources['akshare'] = AkShareDataAcquirer()
            logger.info("✅ AkShare client initialized")
        except Exception as e:
            logger.warning(f"❌ Failed to initialize AkShare client: {e}")

        try:
            self.data_sources['tushare'] = TushareDataAcquirer()
            logger.info("✅ Tushare client initialized")
        except Exception as e:
            logger.warning(f"❌ Failed to initialize Tushare client: {e}")

        # 移除不可用的数据源
        unavailable_sources = [k for k, v in self.data_sources.items() if v is None]
        for source in unavailable_sources:
            del self.data_sources[source]
            logger.warning(f"⚠️ {source} client unavailable, removed from active sources")

        logger.info(f"Active data sources: {list(self.data_sources.keys())}")

        # 数据源优先级（BaoStock优先，因为其稳定性和CSI300专用支持）
        priority_order = ['baostock', 'yahoo', 'akshare', 'tushare']
        self.source_priority = [source for source in priority_order if source in self.data_sources.keys()]

        # 数据源健康状态（只包含可用的数据源）
        self.source_health = {
            source: {'status': 'unknown', 'last_check': None, 'consecutive_failures': 0}
            for source in self.data_sources.keys()
        }

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'source_usage': {source: 0 for source in self.data_sources.keys()}
        }

    def check_source_health(self, source_name: str) -> bool:
        """检查数据源健康状态"""
        client = self.data_sources[source_name]

        try:
            logger.info(f"Checking health of {source_name}...")

            if source_name == 'baostock':
                # BaoStock测试 - 尝试登录和获取少量数据
                if client.login():
                    test_data = client.download_stock_data("sh.600000", "2024-12-01", "2024-12-05")
                    health = test_data is not None and len(test_data) > 0
                    client.logout()
                else:
                    health = False
            elif source_name == 'yahoo':
                # Yahoo Finance测试
                health = client.test_connectivity()
            elif source_name == 'akshare':
                # AkShare测试 - 尝试获取少量数据
                test_symbol = "000001.SS"
                test_data = client.get_stock_daily_data(test_symbol, "2024-12-01", "2024-12-31")
                health = test_data is not None and len(test_data) > 0
            elif source_name == 'tushare':
                # Tushare测试
                test_symbol = "000001.SS"
                test_data = client.get_stock_daily_data(test_symbol, "2024-12-01", "2024-12-31")
                health = test_data is not None and len(test_data) > 0
            else:
                health = False

            # 更新健康状态
            self.source_health[source_name]['status'] = 'healthy' if health else 'unhealthy'
            self.source_health[source_name]['last_check'] = datetime.now()

            if health:
                self.source_health[source_name]['consecutive_failures'] = 0
                logger.info(f"✅ {source_name} is healthy")
            else:
                self.source_health[source_name]['consecutive_failures'] += 1
                logger.warning(f"❌ {source_name} is unhealthy (failures: {self.source_health[source_name]['consecutive_failures']})")

            return health

        except Exception as e:
            logger.error(f"Health check failed for {source_name}: {e}")
            self.source_health[source_name]['status'] = 'error'
            self.source_health[source_name]['last_check'] = datetime.now()
            self.source_health[source_name]['consecutive_failures'] += 1
            return False

    def get_best_available_source(self) -> Optional[str]:
        """获取当前可用的最佳数据源"""
        available_sources = []

        for source_name in self.source_priority:
            # 跳过已经失败多次的数据源
            if self.source_health[source_name]['consecutive_failures'] >= 3:
                logger.warning(f"Skipping {source_name} (too many failures)")
                continue

            # 检查数据源健康状态
            if self.source_health[source_name]['status'] == 'healthy':
                # 如果上次检查超过5分钟，重新检查
                if (self.source_health[source_name]['last_check'] is None or
                    datetime.now() - self.source_health[source_name]['last_check'] > timedelta(minutes=5)):
                    if self.check_source_health(source_name):
                        available_sources.append(source_name)
                else:
                    available_sources.append(source_name)
            else:
                # 尝试检查数据源
                if self.check_source_health(source_name):
                    available_sources.append(source_name)

        if available_sources:
            best_source = available_sources[0]
            logger.info(f"Selected best available source: {best_source}")
            return best_source
        else:
            logger.warning("No healthy data sources available")
            return None

    def download_stock_with_fallback(self, symbol: str, start_date: str, end_date: str,
                                   max_attempts: int = 3) -> Optional[pd.DataFrame]:
        """带回退机制的股票数据下载"""
        self.stats['total_requests'] += 1

        for attempt in range(max_attempts):
            best_source = self.get_best_available_source()

            if best_source is None:
                logger.error("No available data sources")
                self.stats['failed_downloads'] += 1
                return None

            logger.info(f"Attempting to download {symbol} using {best_source} (attempt {attempt + 1})")
            self.stats['source_usage'][best_source] += 1

            try:
                client = self.data_sources[best_source]

                if best_source == 'baostock':
                    # 转换股票代码格式: 000001.SS -> sh.000001 或 sz.000001
                    baostock_symbol = self._convert_to_baostock_format(symbol)
                    if baostock_symbol and client.login():
                        data = client.download_stock_data(baostock_symbol, start_date, end_date)
                        client.logout()
                    else:
                        data = None
                elif best_source == 'yahoo':
                    data = client.download_single_stock(symbol, start_date, end_date)
                else:
                    data = client.get_stock_daily_data(symbol, start_date, end_date)

                if data is not None and len(data) > 0:
                    self.stats['successful_downloads'] += 1
                    logger.info(f"✅ Successfully downloaded {symbol} using {best_source}")
                    return data
                else:
                    logger.warning(f"No data returned from {best_source} for {symbol}")
                    # 标记数据源为不健康
                    self.source_health[best_source]['status'] = 'unhealthy'
                    continue

            except Exception as e:
                logger.error(f"Error downloading {symbol} from {best_source}: {e}")
                # 标记数据源为不健康
                self.source_health[best_source]['status'] = 'error'
                continue

        logger.error(f"Failed to download {symbol} after {max_attempts} attempts")
        self.stats['failed_downloads'] += 1
        return None

    def download_multiple_stocks_smart(self, symbols: List[str], start_date: str, end_date: str,
                                        max_concurrent: int = 3) -> Dict[str, pd.DataFrame]:
        """智能多股票下载"""
        results = {}
        failed_symbols = []

        logger.info(f"Starting smart download of {len(symbols)} symbols")
        logger.info(f"Max concurrent downloads: {max_concurrent}")

        # 分批处理以避免过载
        batch_size = max_concurrent
        total_batches = (len(symbols) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]

            logger.info(f"Processing batch {batch_num + 1}/{total_batches}: {batch_symbols}")

            # 对于Yahoo Finance，使用批量下载
            yahoo_client = self.data_sources['yahoo']
            if (self.source_health['yahoo']['status'] == 'healthy' and
                len(batch_symbols) <= 5):  # Yahoo Finance批量限制
                try:
                    logger.info(f"Using Yahoo Finance batch download for {len(batch_symbols)} symbols")
                    batch_results = yahoo_client.download_multiple_stocks_batch(
                        batch_symbols, start_date, end_date
                    )
                    results.update(batch_results)

                    # 标记成功的股票
                    for symbol in batch_symbols:
                        if symbol in batch_results:
                            self.stats['successful_downloads'] += 1
                            self.stats['source_usage']['yahoo'] += 1
                        else:
                            failed_symbols.append(symbol)

                    continue

                except Exception as e:
                    logger.warning(f"Yahoo Finance batch download failed: {e}")
                    # 回退到单个下载

            # 单个下载（回退方案）
            for symbol in batch_symbols:
                if symbol not in results:  # 如果批量下载没有成功
                    data = self.download_stock_with_fallback(symbol, start_date, end_date)
                    if data is not None:
                        results[symbol] = data
                    else:
                        failed_symbols.append(symbol)

            # 批次间延迟
            if batch_num < total_batches - 1:
                delay = 5.0  # 批次间延迟5秒
                logger.info(f"Waiting {delay}s before next batch...")
                time.sleep(delay)

        # 最终统计
        success_count = len(results)
        total_count = len(symbols)
        success_rate = success_count / total_count * 100 if total_count > 0 else 0

        logger.info(f"Smart download completed:")
        logger.info(f"  Total symbols: {total_count}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Failed: {len(failed_symbols)}")
        logger.info(f"  Success rate: {success_rate:.1f}%")

        # 详细的统计信息
        logger.info(f"Source usage: {self.stats['source_usage']}")
        logger.info(f"Overall stats: {self.stats}")

        return results

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """获取综合报告"""
        return {
            'source_health': self.source_health,
            'statistics': self.stats,
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 分析各数据源状态
        for source_name, health in self.source_health.items():
            if health['consecutive_failures'] >= 3:
                recommendations.append(
                    f"考虑更换或升级 {source_name.upper()} 数据源"
                )
            elif health['status'] == 'unhealthy':
                recommendations.append(
                    f"{source_name.upper()} 暂时不可用，建议等待或使用备用方案"
                )

        # 分析成功率
        if self.stats['total_requests'] > 0:
            success_rate = self.stats['successful_downloads'] / self.stats['total_requests']
            if success_rate < 0.5:
                recommendations.append(
                    f"整体成功率较低 ({success_rate:.1%})，建议检查网络连接或数据源配置"
                )
        else:
            recommendations.append("暂无下载数据，建议测试数据源连接")

        # 分析数据源使用情况
        if self.stats['total_requests'] > 0:
            # 找到使用最多的数据源，确保至少有一次使用
            source_usage_items = [(source, count) for source, count in self.stats['source_usage'].items() if count > 0]
            if source_usage_items:
                primary_source = max(source_usage_items, key=lambda x: x[1])[0]
                if self.stats['source_usage'][primary_source] / self.stats['total_requests'] > 0.8:
                    recommendations.append(
                        f"过度依赖 {primary_source.upper()}，建议增加数据源多样性"
                    )

        if not recommendations:
            recommendations.append("所有数据源工作正常，当前配置良好")

        return recommendations

    def _convert_to_baostock_format(self, symbol: str) -> Optional[str]:
        """
        将股票代码转换为BaoStock格式

        Args:
            symbol: 原始格式，如 "000001.SS" 或 "600000.SS"

        Returns:
            str: BaoStock格式，如 "sz.000001" 或 "sh.600000"
        """
        try:
            if '.' not in symbol:
                return None

            code, exchange = symbol.split('.')

            # 转换交易所代码
            if exchange == 'SS':  # 上海证券交易所
                return f"sh.{code}"
            elif exchange == 'SZ':  # 深圳证券交易所
                return f"sz.{code}"
            else:
                logger.warning(f"Unknown exchange: {exchange}")
                return None

        except Exception as e:
            logger.error(f"Error converting symbol {symbol}: {e}")
            return None

    def download_csi300_with_baostock(self, start_date: str = '2020-01-01', end_date: str = None) -> Dict[str, Any]:
        """
        使用BaoStock专门下载CSI300数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 下载结果
        """
        if 'baostock' not in self.data_sources:
            logger.error("BaoStock client not available")
            return {'success': False, 'error': 'BaoStock client not available'}

        client = self.data_sources['baostock']

        try:
            logger.info("🎯 Using BaoStock for CSI300 download...")
            results = client.download_csi300_complete(start_date, end_date, save_to_file=True)

            if results['success']:
                # 更新统计信息
                self.stats['successful_downloads'] += results['successful']
                self.stats['failed_downloads'] += results['failed']
                self.stats['source_usage']['baostock'] += results['successful']

                logger.info(f"✅ BaoStock CSI300 download completed: {results['successful']}/{results['total_stocks']} successful")

            return results

        except Exception as e:
            logger.error(f"❌ BaoStock CSI300 download failed: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """测试函数"""
    manager = SmartDataSourceManager()

    # 检查所有数据源健康状态
    logger.info("=== Checking Data Source Health ===")
    for source in manager.data_sources.keys():
        manager.check_source_health(source)

    # 生成综合报告
    report = manager.get_comprehensive_report()
    logger.info("=== Comprehensive Report ===")
    logger.info(f"Source Health: {report['source_health']}")
    logger.info(f"Statistics: {report['statistics']}")
    logger.info(f"Recommendations: {report['recommendations']}")

    # 测试智能下载
    test_symbols = ["000001.SS", "600519.SS"]
    start_date = "2024-12-01"
    end_date = "2024-12-31"

    logger.info(f"\n=== Testing Smart Download ===")
    results = manager.download_multiple_stocks_smart(test_symbols, start_date, end_date)

    for symbol, data in results.items():
        if data is not None:
            logger.info(f"{symbol}: {len(data)} records")
        else:
            logger.warning(f"{symbol}: Failed to download")

    # 如果BaoStock可用，测试CSI300下载
    if 'baostock' in manager.data_sources:
        logger.info(f"\n=== Testing BaoStock CSI300 Download ===")
        csi300_results = manager.download_csi300_with_baostock(start_date, end_date)
        logger.info(f"CSI300 Download: {csi300_results.get('success', False)}")
        if csi300_results.get('success'):
            logger.info(f"  Downloaded: {csi300_results['successful']}/{csi300_results['total_stocks']} stocks")
            logger.info(f"  Total records: {csi300_results['total_records']:,}")
        else:
            logger.error(f"  Error: {csi300_results.get('error', 'Unknown error')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()