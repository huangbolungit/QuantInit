#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整CSI800数据下载器 - 下载全部800只中证800成分股数据
包含CSI300(300只) + CSI500(500只) = CSI800(800只)
"""

import os
import sys
import logging
import time
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.data_acquisition.baostock_client import BaoStockClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_csi800_download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompleteCSI800Downloader:
    """完整CSI800数据下载器"""

    def __init__(self):
        self.client = BaoStockClient()
        self.base_data_dir = Path("data/historical/stocks/complete_csi800")
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

        # 数据字段配置
        self.fields = 'date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM'

        # 时间范围：5年历史数据
        self.start_date = '2020-01-01'
        self.end_date = '2024-12-31'

        # 批次配置
        self.batch_size = 50  # 每批50只股票

    def get_complete_csi800_list(self) -> pd.DataFrame:
        """获取完整的CSI800成分股列表"""
        logger.info("🔍 获取完整CSI800成分股列表...")

        try:
            if not self.client.login():
                logger.error("❌ BaoStock登录失败")
                return pd.DataFrame()

            # 获取CSI300成分股
            logger.info("📊 获取CSI300成分股...")
            csi300_stocks = self.client.get_csi300_constituents()

            # 获取CSI500成分股
            logger.info("📊 获取CSI500成分股...")
            csi500_stocks = self.client.get_csi500_constituents()

            if csi300_stocks.empty or csi500_stocks.empty:
                logger.error("❌ 获取成分股数据失败")
                return pd.DataFrame()

            # 合并CSI300和CSI500，去重得到CSI800
            logger.info("🔗 合并CSI300和CSI500成分股...")
            all_stocks = pd.concat([csi300_stocks, csi500_stocks], ignore_index=True)
            all_stocks = all_stocks.drop_duplicates(subset=['code'])

            logger.info(f"✅ 成功获取CSI800成分股: {len(all_stocks)} 只")
            logger.info(f"   - CSI300: {len(csi300_stocks)} 只")
            logger.info(f"   - CSI500: {len(csi500_stocks)} 只")

            # 保存完整列表
            list_file = self.base_data_dir / "csi800_complete_list.csv"
            all_stocks.to_csv(list_file, index=False, encoding='utf-8-sig')
            logger.info(f"💾 CSI800完整列表已保存: {list_file}")

            self.client.logout()
            return all_stocks

        except Exception as e:
            logger.error(f"❌ 获取CSI800成分股异常: {e}")
            return pd.DataFrame()

    def download_stock_data(self, stock_code: str, stock_name: str = "") -> bool:
        """下载单只股票数据"""
        try:
            # 转换股票代码格式
            baostock_code = self.client._convert_to_baostock_format(stock_code)

            # 下载数据
            data = self.client.download_stock_data(
                baostock_code,
                self.start_date,
                self.end_date
            )

            if data is None or data.empty:
                logger.warning(f"⚠️ {stock_code} 无数据")
                return False

            # 添加额外信息
            data['stock_name'] = stock_name
            data['download_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 按年份保存数据
            data['date'] = pd.to_datetime(data['date'])
            for year, year_data in data.groupby(data['date'].dt.year):
                year_dir = self.base_data_dir / "stocks" / str(year)
                year_dir.mkdir(parents=True, exist_ok=True)

                file_path = year_dir / f"{stock_code}.csv"
                year_data.to_csv(file_path, index=False, encoding='utf-8-sig')

            logger.info(f"✅ {stock_code} ({stock_name}) 成功: {len(data)} 条记录")
            return True

        except Exception as e:
            logger.error(f"❌ {stock_code} 下载失败: {e}")
            return False

    def get_existing_stocks(self) -> set:
        """获取已下载的股票列表"""
        existing_stocks = set()
        stocks_dir = self.base_data_dir / "stocks"

        if stocks_dir.exists():
            for year_dir in stocks_dir.iterdir():
                if year_dir.is_dir():
                    for file_path in year_dir.glob("*.csv"):
                        stock_code = file_path.stem
                        existing_stocks.add(stock_code)

        return existing_stocks

    def download_missing_stocks(self, csi800_list: pd.DataFrame) -> None:
        """下载缺失的股票数据"""
        logger.info("🔍 检查已下载股票...")

        existing_stocks = self.get_existing_stocks()
        logger.info(f"📊 已下载股票: {len(existing_stocks)} 只")

        # 处理股票代码格式，提取纯数字代码
        def extract_stock_code(code_str):
            if isinstance(code_str, str) and '.' in code_str:
                return code_str.split('.')[1]  # 提取 'sh.600000' -> '600000'
            return str(code_str).zfill(6)  # 确保6位数字格式

        all_stocks = set(extract_stock_code(code) for code in csi800_list['code'])
        missing_stocks = list(all_stocks - existing_stocks)

        logger.info(f"📊 缺失股票: {len(missing_stocks)} 只")

        if not missing_stocks:
            logger.info("✅ 所有CSI800股票数据已完整")
            return

        # 准备下载列表
        download_list = []
        for stock_code in missing_stocks:
            # 查找匹配的股票信息
            matching_stocks = csi800_list[csi800_list['code'].apply(lambda x: extract_stock_code(x)) == stock_code]
            if not matching_stocks.empty:
                stock_name = matching_stocks['code_name'].iloc[0]
                download_list.append((stock_code, stock_name))

        logger.info(f"🚀 开始下载 {len(download_list)} 只缺失股票...")

        # 分批下载
        total_batches = (len(download_list) + self.batch_size - 1) // self.batch_size
        successful = 0
        failed = 0

        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(download_list))
            batch = download_list[start_idx:end_idx]

            logger.info(f"📦 处理批次 {batch_num + 1}/{total_batches}: {len(batch)} 只股票")

            if not self.client.login():
                logger.error("❌ BaoStock登录失败，跳过此批次")
                continue

            batch_successful = 0
            batch_failed = 0

            for stock_code, stock_name in batch:
                if self.download_stock_data(stock_code, stock_name):
                    batch_successful += 1
                    successful += 1
                else:
                    batch_failed += 1
                    failed += 1

            self.client.logout()

            logger.info(f"📊 批次 {batch_num + 1} 完成: 成功 {batch_successful}, 失败 {batch_failed}")

            # 批次间休息
            if batch_num < total_batches - 1:
                logger.info("⏳ 批次间休息 5 秒...")
                time.sleep(5)

        # 最终统计
        logger.info("=" * 60)
        logger.info("🎯 CSI800完整数据下载统计:")
        logger.info(f"   目标股票数: 800")
        logger.info(f"   已有股票数: {len(existing_stocks)}")
        logger.info(f"   需要下载: {len(download_list)}")
        logger.info(f"   下载成功: {successful}")
        logger.info(f"   下载失败: {failed}")
        logger.info(f"   最终完成: {len(existing_stocks) + successful}/800")
        logger.info("=" * 60)

    def validate_download_completeness(self) -> bool:
        """验证下载完整性"""
        logger.info("🔍 验证CSI800数据下载完整性...")

        # 读取CSI800完整列表
        list_file = self.base_data_dir / "csi800_complete_list.csv"
        if not list_file.exists():
            logger.error("❌ CSI800完整列表文件不存在")
            return False

        csi800_list = pd.read_csv(list_file)

        # 处理股票代码格式，提取纯数字代码
        def extract_stock_code(code_str):
            if isinstance(code_str, str) and '.' in code_str:
                return code_str.split('.')[1]  # 提取 'sh.600000' -> '600000'
            return str(code_str).zfill(6)  # 确保6位数字格式

        expected_stocks = set(extract_stock_code(code) for code in csi800_list['code'])
        logger.info(f"📊 期望股票数: {len(expected_stocks)}")

        # 检查已下载股票
        existing_stocks = self.get_existing_stocks()
        logger.info(f"📊 实际下载股票数: {len(existing_stocks)}")

        # 计算完成率
        completion_rate = len(existing_stocks) / len(expected_stocks) * 100
        logger.info(f"📊 完成率: {completion_rate:.1f}%")

        # 找出缺失股票
        missing_stocks = expected_stocks - existing_stocks
        if missing_stocks:
            logger.warning(f"⚠️ 仍有 {len(missing_stocks)} 只股票缺失")
            logger.warning(f"缺失股票示例: {list(missing_stocks)[:10]}")
            return False
        else:
            logger.info("✅ CSI800数据下载完整！")
            return True

def main():
    """主函数"""
    logger.info("🚀 CSI800完整数据下载器启动")

    downloader = CompleteCSI800Downloader()

    # 1. 获取CSI800完整列表
    csi800_list = downloader.get_complete_csi800_list()
    if csi800_list.empty:
        logger.error("❌ 无法获取CSI800成分股列表，退出")
        return

    # 2. 下载缺失股票数据
    downloader.download_missing_stocks(csi800_list)

    # 3. 验证下载完整性
    is_complete = downloader.validate_download_completeness()

    if is_complete:
        logger.info("🎉 CSI800完整数据下载任务完成！")
    else:
        logger.warning("⚠️ CSI800数据下载未完全完成，可能需要重试缺失部分")

if __name__ == "__main__":
    main()