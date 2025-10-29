#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版CSI300 BaoStock下载器 - 直接使用BaoStock客户端下载缺失股票
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.data_acquisition.baostock_client import BaoStockClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_baostock_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_existing_stocks(data_dir: Path) -> set:
    """获取已下载的股票代码"""
    existing_stocks = set()

    # 遍历所有年份目录
    for year_dir in data_dir.glob("csi300_*"):
        stocks_dir = year_dir / "stocks"
        if stocks_dir.exists():
            for csv_file in stocks_dir.glob("*.csv"):
                stock_code = csv_file.stem
                if stock_code.isdigit() and len(stock_code) == 6:
                    existing_stocks.add(stock_code)

    logger.info(f"发现已下载的股票: {len(existing_stocks)} 只")
    return existing_stocks

def get_missing_stocks(existing_stocks: set) -> list:
    """获取需要下载的缺失股票列表"""
    client = BaoStockClient()

    try:
        if client.login():
            csi300_data = client.get_csi300_constituents()
            client.logout()

            if csi300_data is not None:
                # 提取所有股票代码
                all_stocks = set()
                for code in csi300_data['code']:
                    stock_code = code.split('.')[1]
                    all_stocks.add(stock_code)

                # 找出缺失的股票
                missing_stocks = all_stocks - existing_stocks

                logger.info(f"CSI300总股票数: {len(all_stocks)}")
                logger.info(f"已下载股票数: {len(existing_stocks)}")
                logger.info(f"需要下载股票数: {len(missing_stocks)}")

                return sorted(list(missing_stocks))
            else:
                logger.error("无法获取CSI300成分股列表")
                return []
        else:
            logger.error("BaoStock登录失败")
            return []

    except Exception as e:
        logger.error(f"获取缺失股票列表失败: {e}")
        return []

def download_missing_stocks_simple(stock_list: list, batch_size: int = 50) -> dict:
    """简化版批量下载缺失股票数据"""
    if not stock_list:
        logger.info("没有需要下载的股票")
        return {'success': True, 'message': 'No stocks to download'}

    client = BaoStockClient()

    if not client.login():
        logger.error("BaoStock登录失败")
        return {'success': False, 'error': 'BaoStock login failed'}

    try:
        logger.info(f"开始下载 {len(stock_list)} 只缺失的CSI300股票...")
        logger.info(f"批量大小: {batch_size}")

        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        results = {
            'total_stocks': len(stock_list),
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_records': 0,
            'failed_stocks': [],
            'start_time': datetime.now()
        }

        # 分批下载
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(stock_list))
            batch_stocks = stock_list[start_idx:end_idx]

            logger.info(f"处理第 {batch_num + 1}/{total_batches} 批次: {len(batch_stocks)} 只股票")

            # 转换为BaoStock格式
            baostock_codes = []
            for stock in batch_stocks:
                if stock.startswith('6'):
                    baostock_codes.append(f"sh.{stock}")
                else:
                    baostock_codes.append(f"sz.{stock}")

            # 下载本批次股票
            batch_results = client.download_multiple_stocks(
                stock_codes=baostock_codes,
                start_date='2020-01-01',
                end_date='2024-12-31',
                save_to_file=True
            )

            # 更新统计
            results['successful_downloads'] += batch_results['successful']
            results['failed_downloads'] += batch_results['failed']
            results['total_records'] += batch_results['total_records']
            results['failed_stocks'].extend(batch_results['failed_stocks'])

            logger.info(f"批次 {batch_num + 1} 完成: 成功 {batch_results['successful']}, 失败 {batch_results['failed']}")

            # 进度报告
            progress = (batch_num + 1) / total_batches * 100
            logger.info(f"总进度: {progress:.1f}% - 成功: {results['successful_downloads']}, 失败: {results['failed_downloads']}")

            # 批次间延迟
            if batch_num < total_batches - 1:
                import time
                time.sleep(5)  # 批次间延迟5秒

        # 最终统计
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        results['success_rate'] = results['successful_downloads'] / results['total_stocks'] * 100

        return results

    finally:
        client.logout()

def main():
    """主函数"""
    logger.info("🚀 简化版CSI300 BaoStock下载器启动")

    # 数据目录
    data_dir = Path("backend/data/historical/stocks")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. 获取已下载的股票
        logger.info("📋 检查已下载的股票...")
        existing_stocks = get_existing_stocks(data_dir)

        # 2. 获取需要下载的股票
        logger.info("🔍 获取缺失的股票列表...")
        missing_stocks = get_missing_stocks(existing_stocks)

        if not missing_stocks:
            logger.info("✅ 所有CSI300股票已下载完成！")
            return

        # 显示一些示例缺失股票
        logger.info(f"缺失股票示例: {missing_stocks[:10]}")

        # 3. 开始下载
        logger.info("📥 开始下载缺失的股票...")
        results = download_missing_stocks_simple(missing_stocks, batch_size=50)

        # 4. 显示最终结果
        logger.info("=" * 80)
        logger.info("📊 下载完成统计:")
        logger.info(f"  总股票数: {results['total_stocks']}")
        logger.info(f"  成功下载: {results['successful_downloads']}")
        logger.info(f"  下载失败: {results['failed_downloads']}")
        logger.info(f"  成功率: {results['success_rate']:.1f}%")
        logger.info(f"  总记录数: {results['total_records']:,}")
        logger.info(f"  用时: {results['duration']}")

        if results['failed_stocks']:
            logger.warning(f"  失败股票: {results['failed_stocks'][:20]}...")
            if len(results['failed_stocks']) > 20:
                logger.warning(f"  ... 还有 {len(results['failed_stocks']) - 20} 只股票失败")

        if results['success_rate'] >= 95:
            logger.info("🎉 CSI300数据下载基本完成！")
        elif results['success_rate'] >= 80:
            logger.info("✅ CSI300数据下载大部分完成，少量失败可稍后重试")
        else:
            logger.warning("⚠️ 下载成功率较低，建议检查网络连接或重试")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 下载过程出现异常: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()