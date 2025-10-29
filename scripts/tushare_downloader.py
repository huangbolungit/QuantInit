#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare数据下载脚本 - 命令行工具
"""

import sys
import argparse
from pathlib import Path
import os

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.data_acquisition.tushare_client import TushareDataAcquirer


def main():
    parser = argparse.ArgumentParser(description="A股历史数据下载工具 (Tushare版)")
    parser.add_argument("--mode", choices=["sample", "csi300", "custom"], default="sample",
                       help="下载模式: sample=样本数据, csi300=沪深300成分股, custom=自定义股票")
    parser.add_argument("--days", type=int, default=365,
                       help="样本数据的天数（仅sample模式有效）")
    parser.add_argument("--start-date", type=str, help="开始日期 YYYYMMDD")
    parser.add_argument("--end-date", type=str, help="结束日期 YYYYMMDD")
    parser.add_argument("--max-stocks", type=int, help="最大下载数量（用于测试）")
    parser.add_argument("--data-dir", type=str, help="数据存储目录")
    parser.add_argument("--stocks", type=str, help="指定股票代码，逗号分隔（custom模式使用）")
    parser.add_argument("--token", type=str, help="Tushare API token（可选，默认从环境变量读取）")

    args = parser.parse_args()

    print("A股智能投顾助手 - Tushare数据下载工具")
    print("=" * 50)

    # 检查Tushare token
    token = args.token or os.getenv('TUSHARE_TOKEN')
    if not token:
        print("错误: 请提供Tushare token")
        print("方法1: 设置环境变量 TUSHARE_TOKEN")
        print("方法2: 使用 --token 参数")
        print("获取token: https://tushare.pro/document/1?doc_id=109")
        sys.exit(1)

    try:
        # 创建数据获取器
        acquirer = TushareDataAcquirer(args.data_dir, token)

        if args.mode == "sample":
            print(f"下载样本数据，最近 {args.days} 天")
            acquirer.download_sample_data(days=args.days)

        elif args.mode == "csi300":
            if not args.start_date or not args.end_date:
                # 默认下载最近2年数据
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
            else:
                start_date = args.start_date
                end_date = args.end_date

            print(f"下载沪深300成分股数据: {start_date} 到 {end_date}")
            acquirer.download_csi300_data(start_date, end_date, args.max_stocks)

        elif args.mode == "custom":
            if not args.stocks:
                print("错误: custom模式需要指定股票代码 --stocks")
                sys.exit(1)

            if not args.start_date or not args.end_date:
                # 默认下载最近1年数据
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            else:
                start_date = args.start_date
                end_date = args.end_date

            stock_list = [s.strip() for s in args.stocks.split(",")]
            print(f"下载指定股票数据: {', '.join(stock_list)}")
            print(f"时间范围: {start_date} 到 {end_date}")

            # 获取基本信息
            acquirer.get_stock_basic_info(stock_list)

            # 下载每只股票的数据
            success_count = 0
            for stock_code in stock_list:
                print(f"下载 {stock_code}...")
                df = acquirer.get_stock_daily_data(stock_code, start_date, end_date)
                if not df.empty:
                    if acquirer.save_stock_data(stock_code, df):
                        success_count += 1
                        print(f"  {stock_code} 下载成功: {len(df)} 条记录")
                    else:
                        print(f"  {stock_code} 保存失败")
                else:
                    print(f"  {stock_code} 无数据")

            print(f"下载完成! 成功: {success_count}/{len(stock_list)}")

        print("数据下载完成!")

        # 验证数据质量
        if args.mode == "sample":
            test_stock = '000001'  # 测试平安银行数据
            quality = acquirer.validate_data_quality(test_stock)
            print(f"\n股票 {test_stock} 数据质量验证:")
            for key, value in quality.items():
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"下载失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()