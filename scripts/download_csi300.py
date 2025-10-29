#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪深300真实历史数据下载器 - 简化版本
解决Windows编码问题的版本
"""

import sys
import time
import pandas as pd
import akshare as ak
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

print("沪深300数据下载器启动")
print("=" * 50)

def download_stock_data(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """下载单只股票数据"""
    try:
        # AkShare的stock_zh_a_hist函数直接使用6位股票代码，不需要后缀
        symbol = stock_code

        print(f"正在下载 {stock_code}...")

        # 下载数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )

        if df.empty:
            print(f"警告: {stock_code} 无数据")
            return None

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

        # 数据类型转换
        df['date'] = pd.to_datetime(df['date'])
        df['stock_code'] = stock_code

        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        print(f"成功下载 {stock_code}: {len(df)} 条记录")
        return df

    except Exception as e:
        print(f"错误: 下载 {stock_code} 失败: {e}")
        return None

def save_stock_data(stock_code: str, df: pd.DataFrame):
    """保存股票数据"""
    try:
        # 创建目录
        data_dir = Path("data/historical/stocks/2024")
        data_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        filename = data_dir / f"{stock_code}.csv"
        df.to_csv(filename, index=False)
        print(f"已保存: {filename}")

    except Exception as e:
        print(f"错误: 保存 {stock_code} 失败: {e}")

def get_csi300_stocks():
    """获取沪深300成分股"""
    try:
        print("正在获取沪深300成分股...")

        # 方法1: 使用AkShare
        csi300_df = ak.index_stock_cons(index_code="000300")
        if not csi300_df.empty:
            stock_codes = csi300_df['品种代码'].tolist()
            stock_codes = [code.zfill(6) for code in stock_codes if code]
            print(f"成功获取沪深300成分股: {len(stock_codes)}只")
            return stock_codes
        else:
            print("方法1失败，尝试备用方法...")

    except Exception as e:
        print(f"获取成分股失败: {e}")

    # 使用预定义的主要成分股
    print("使用预定义的沪深300主要成分股...")
    return [
        # 金融股
        '000001', '000002', '600000', '600036', '600016', '601318', '601398',
        # 消费股
        '000858', '600519', '000568', '600779', '000596', '600887',
        # 科技股
        '000063', '002415', '300750', '000725', '002230', '300059',
        # 医药股
        '000423', '600276', '000661', '300015', '300003', '300122',
        # 其他重要股票
        '600309', '002648', '000792', '600160', '000425', '600031'
    ]

def download_sample_stocks():
    """下载样本股票数据"""
    # 测试股票
    sample_stocks = ['000001', '000002', '600519', '600036', '000858', '601318']

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    print(f"下载样本数据: {start_date_str} 到 {end_date_str}")
    print(f"股票数量: {len(sample_stocks)}")

    success_count = 0
    failed_stocks = []

    for i, stock_code in enumerate(sample_stocks, 1):
        print(f"进度: {i}/{len(sample_stocks)} - {stock_code}")

        df = download_stock_data(stock_code, start_date_str, end_date_str)
        if df is not None and not df.empty:
            save_stock_data(stock_code, df)
            success_count += 1
        else:
            failed_stocks.append(stock_code)

        # API延迟
        time.sleep(1)

    print("=" * 50)
    print("下载完成!")
    print(f"成功: {success_count} 只")
    print(f"失败: {len(failed_stocks)} 只")

    if failed_stocks:
        print("失败股票:", ", ".join(failed_stocks))

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="沪深300数据下载器")
    parser.add_argument("--test", action="store_true", help="测试模式 - 下载样本数据")
    parser.add_argument("--years", type=int, default=5, help="下载年数")
    parser.add_argument("--stocks", type=str, help="指定股票代码，逗号分隔")

    args = parser.parse_args()

    if args.test:
        print("测试模式: 下载样本数据")
        download_sample_stocks()
    elif args.stocks:
        print("自定义股票模式")
        stock_codes = [s.strip() for s in args.stocks.split(",")]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.years * 365)
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        print(f"下载自定义股票: {stock_codes}")
        print(f"时间范围: {start_date_str} 到 {end_date_str}")

        for stock_code in stock_codes:
            df = download_stock_data(stock_code, start_date_str, end_date_str)
            if df is not None:
                save_stock_data(stock_code, df)
            time.sleep(1)
    else:
        print("默认模式: 下载样本数据")
        download_sample_stocks()

if __name__ == "__main__":
    main()