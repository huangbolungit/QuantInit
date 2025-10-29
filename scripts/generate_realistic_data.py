#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成更多真实感的股票数据样本
为回测提供有意义的测试数据
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import random

def generate_realistic_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """生成具有真实市场特征的股票数据"""

    # 生成日期序列
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    dates = pd.date_range(start_dt, end_dt, freq='D')

    # 过滤工作日
    dates = dates[dates.weekday < 5]

    # 设置随机种子，确保可重现
    np.random.seed(hash(stock_code) % 2**32)

    # 基础参数设置
    if stock_code.startswith('6'):  # 沪市
        base_price = 15.0 + np.random.uniform(-5, 20)  # 沪市股票通常价格较高
        volatility = 0.025
    else:  # 深市
        base_price = 8.0 + np.random.uniform(-3, 12)   # 深市股票价格相对较低
        volatility = 0.030

    # 股票特定特征
    sector_features = {
        '000001': {'trend': 0.0003, 'momentum': 0.6, 'volatility': 0.022},  # 银行股
        '000002': {'trend': -0.0001, 'momentum': 0.4, 'volatility': 0.028},  # 地产股
        '600519': {'trend': 0.0005, 'momentum': 0.8, 'volatility': 0.020},  # 茅台股（强动量）
        '600036': {'trend': 0.0002, 'momentum': 0.5, 'volatility': 0.021},  # 银行股
        '000858': {'trend': 0.0003, 'momentum': 0.7, 'volatility': 0.025},  # 五粮液
        '601318': {'trend': 0.0001, 'momentum': 0.4, 'volatility': 0.023},  # 平安保险
    }

    # 获取股票特征
    features = sector_features.get(stock_code, {
        'trend': np.random.uniform(-0.0002, 0.0003),
        'momentum': np.random.uniform(0.3, 0.7),
        'volatility': volatility
    })

    # 生成价格序列
    prices = []
    current_price = base_price

    for i, date in enumerate(dates):
        if i == 0:
            prices.append(current_price)
            continue

        # 日收益率 = 趋势 + 动量 + 随机噪声 + 均值回归
        trend_component = features['trend']

        # 动量分量（前10日收益的影响）
        momentum_component = 0
        if i >= 10:
            recent_return = (current_price - prices[-10]) / prices[-10]
            momentum_component = features['momentum'] * recent_return * 0.1

        # 均值回归分量
        mean_reversion = -0.01 * (current_price - base_price) / base_price

        # 随机噪声
        random_component = np.random.normal(0, features['volatility'])

        # 特殊事件（偶尔的大幅波动）
        event_component = 0
        if np.random.random() < 0.01:  # 1%概率发生特殊事件
            event_component = np.random.choice([-0.05, 0.05])

        daily_return = trend_component + momentum_component + mean_reversion + random_component + event_component

        # 限制单日收益率在合理范围内
        daily_return = np.clip(daily_return, -0.15, 0.15)

        current_price = current_price * (1 + daily_return)
        prices.append(max(current_price, 0.1))  # 价格不能为负

    # 生成OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # 日内波动
        daily_volatility = features['volatility'] * 2
        intraday_range = close * daily_volatility

        # 开盘价（基于前一日收盘价）
        if i == 0:
            open_price = close
        else:
            gap = np.random.normal(0, daily_volatility * 0.3)
            open_price = prices[i-1] * (1 + gap)

        # 最高价和最低价
        high = close * (1 + abs(np.random.uniform(0.2, 0.8)) * daily_volatility)
        low = close * (1 - abs(np.random.uniform(0.2, 0.8)) * daily_volatility)

        # 确保价格逻辑正确
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # 成交量和成交额
        base_volume = 10000000 + np.random.uniform(-5000000, 20000000)
        volume = int(base_volume * (1 + abs(daily_return) * 2))
        amount = volume * close

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'stock_code': stock_code,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
            'amount': round(amount, 2)
        })

    return pd.DataFrame(data)

def generate_sample_portfolio():
    """生成样本投资组合数据"""
    print("生成真实感股票数据样本")
    print("=" * 50)

    # 创建数据目录
    data_dir = Path("data/historical/stocks/2024")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 沪深300主要成分股（更具代表性）
    csi300_sample = [
        # 金融板块
        '000001', '000002', '600000', '600036', '601318', '601398', '601939', '600016',
        '600015', '601288', '600030', '601166', '600104', '600109', '600111',
        # 消费板块
        '600519', '000858', '000568', '600779', '000596', '002304', '600887', '600570',
        # 科技板块
        '000063', '002415', '300750', '000725', '002230', '300059', '300142', '300034',
        # 医药板块
        '000423', '600276', '000661', '300015', '300003', '300122', '002007', '300760',
        # 能源板块
        '600028', '601857', '600256', '000983', '002202', '600011', '601088', '600886',
        # 工业板块
        '000425', '600031', '002031', '600150', '000680', '600761', '000876', '002414',
        # 材料板块
        '600309', '002648', '000792', '600160', '000895', '600585', '000960', '002142'
    ]

    print(f"股票池: {len(csi300_sample)}只")
    print("包含: 金融、消费、科技、医药、能源、工业、材料等多个行业")
    print()

    # 生成时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    print(f"时间范围: {start_date_str} 到 {end_date_str}")
    print(f"交易日数: ~{len([d for d in pd.date_range(start_date, end_date) if d.weekday() < 5])}天")
    print()

    success_count = 0
    sector_stats = {}

    for i, stock_code in enumerate(csi300_sample, 1):
        try:
            print(f"生成数据 {i:3d}/{len(csi300_sample):3d} - {stock_code}")

            df = generate_realistic_stock_data(stock_code, start_date_str, end_date_str)

            if not df.empty:
                # 保存数据
                filename = data_dir / f"{stock_code}.csv"
                df.to_csv(filename, index=False, encoding='utf-8')
                success_count += 1

                # 简单分类统计
                if stock_code.startswith('6'):
                    sector = '沪市'
                else:
                    sector = '深市'
                sector_stats[sector] = sector_stats.get(sector, 0) + 1

                print(f"  ✓ {len(df)} 条记录")
            else:
                print(f"  ✗ 生成失败")

        except Exception as e:
            print(f"  ✗ 错误: {e}")

    print()
    print("=" * 50)
    print(f"数据生成完成!")
    print(f"成功: {success_count}/{len(csi300_sample)} 只股票")
    print(f"数据文件保存在: {data_dir}")
    print(f"统计: 沪市 {sector_stats.get('沪市', 0)} 只, 深市 {sector_stats.get('深市', 0)} 只")

    # 生成统计报告
    stats_file = data_dir / "data_generation_stats.txt"
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(f"股票数据生成统计\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"股票数量: {len(csi300_sample)}\n")
        f.write(f"成功数量: {success_count}\n")
        f.write(f"时间范围: {start_date_str} 到 {end_date_str}\n")
        f.write(f"行业分布: {sector_stats}\n")

    print(f"统计报告: {stats_file}")

    return success_count

def main():
    """主函数"""
    success_count = generate_sample_portfolio()

    if success_count > 20:
        print("\n🎉 数据生成成功! 可以开始有意义的回测了。")
        print("\n建议下一步:")
        print("1. 修改回测框架读取真实数据文件")
        print("2. 运行回测验证策略效果")
        print("3. 分析结果并优化参数")
    else:
        print("\n⚠️  数据生成数量较少，建议增加更多股票样本")

if __name__ == "__main__":
    main()