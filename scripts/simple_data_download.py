#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单直接的数据下载器
"""

import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime, timedelta

def main():
    print("A股数据下载器 - 简化版本")
    print("=" * 50)

    # 创建数据目录
    data_dir = Path("data/historical/stocks/2024")
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"数据目录: {data_dir}")

    # 测试股票列表
    test_stocks = ['000001', '000002', '600519', '600036']

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=300)  # 下载最近300天数据

    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    print(f"时间范围: {start_date_str} 到 {end_date_str}")
    print(f"股票列表: {test_stocks}")
    print()

    success_count = 0

    for stock_code in test_stocks:
        try:
            print(f"正在下载 {stock_code}...")

            # AkShare的stock_zh_a_hist函数直接使用6位股票代码，不需要后缀
            symbol = stock_code

            # 下载数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date_str,
                end_date=end_date_str,
                adjust="qfq"
            )

            if df.empty:
                print(f"  无数据")
                continue

            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            })

            # 添加股票代码
            df['stock_code'] = stock_code

            # 转换日期
            df['date'] = pd.to_datetime(df['date'])

            # 保存到文件
            filename = data_dir / f"{stock_code}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')

            print(f"  成功: {len(df)} 条记录 -> {filename}")
            success_count += 1

        except Exception as e:
            print(f"  失败: {e}")

    print()
    print("=" * 50)
    print(f"下载完成! 成功: {success_count}/{len(test_stocks)}")

if __name__ == "__main__":
    main()