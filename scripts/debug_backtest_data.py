#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试回测引擎数据加载问题
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def debug_data_loading():
    """调试数据加载逻辑"""

    # 测试参数
    stock_code = "600519"
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    print(f"调试股票数据加载: {stock_code}")
    print(f"时间范围: {start_date} 到 {end_date}")
    print("=" * 50)

    # 数据目录设置
    data_dir = Path("data/historical/stocks/csi300_5year/stocks")
    print(f"数据目录: {data_dir}")
    print(f"目录存在: {data_dir.exists()}")

    # 查找该股票的所有数据文件
    stock_files = sorted(list(data_dir.rglob(f"{stock_code}.csv")))
    print(f"找到 {len(stock_files)} 个数据文件:")

    for i, file_path in enumerate(stock_files):
        print(f"  {i+1}. {file_path}")

        # 检查文件内容
        try:
            df = pd.read_csv(file_path)
            print(f"     文件大小: {len(df)} 行数据")
            print(f"     日期范围: {df['date'].min()} 到 {df['date'].max()}")

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])

            # 筛选日期范围
            filtered_df = df[
                (df['date'] >= start_date) &
                (df['date'] <= end_date)
            ]
            print(f"     筛选后: {len(filtered_df)} 行数据")

            if len(filtered_df) > 0:
                print(f"     前3行数据:")
                print(filtered_df.head(3)[['date', 'open', 'close', 'volume']])

        except Exception as e:
            print(f"     读取失败: {e}")

        print()

    # 测试回测引擎的load_stock_data方法
    print("=" * 50)
    print("测试回测引擎数据加载:")

    try:
        from app.services.backtesting.engine import BacktestEngine
        engine = BacktestEngine(str(data_dir))

        loaded_data = engine.load_stock_data(stock_code, start_date, end_date)
        print(f"引擎加载数据: {len(loaded_data)} 行")

        if len(loaded_data) > 0:
            print("加载成功!")
            print(f"日期范围: {loaded_data['date'].min()} 到 {loaded_data['date'].max()}")
        else:
            print("加载失败: 无数据")

    except Exception as e:
        print(f"引擎加载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_data_loading()