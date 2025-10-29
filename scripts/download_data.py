#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据下载脚本 - 命令行工具
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.data_acquisition.akshare_client import AkShareDataAcquirer


def main():
    parser = argparse.ArgumentParser(description="A股历史数据下载工具")
    parser.add_argument("--mode", choices=["sample", "full"], default="sample",
                       help="下载模式: sample=样本数据, full=全量数据")
    parser.add_argument("--days", type=int, default=365,
                       help="样本数据的天数（仅sample模式有效）")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYYMMDD")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYYMMDD")
    parser.add_argument("--max-stocks", type=int, help="最大下载数量（用于测试）")
    parser.add_argument("--data-dir", type=str, help="数据存储目录")

    args = parser.parse_args()

    print("A股智能投顾助手 - 数据下载工具")
    print("=" * 50)

    # 创建数据获取器
    acquirer = AkShareDataAcquirer(args.data_dir)

    if args.mode == "sample":
        print(f"下载样本数据，最近 {args.days} 天")
        acquirer.download_sample_data(days=args.days)
    else:
        if not args.start_date or not args.end_date:
            # 默认下载最近2年数据
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
        else:
            start_date = args.start_date
            end_date = args.end_date

        print(f"下载全量数据: {start_date} 到 {end_date}")
        acquirer.download_all_stock_data(start_date, end_date, args.max_stocks)

    # 下载行业分类
    acquirer.get_shenwan_sector_classification()

    print("数据下载完成!")


if __name__ == "__main__":
    main()