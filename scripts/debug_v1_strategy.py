#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试V1策略 - 快速验证单只股票的策略性能计算
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.full_sample_factor_validator import FullSampleFactorValidator

def debug_single_stock():
    """调试单只股票的策略计算"""

    backtester = FullSampleFactorValidator()

    # 选择一只股票进行测试
    test_stock = "000001"

    # 加载2022年数据
    data = backtester.load_stock_data(
        test_stock,
        "2022-01-01",
        "2022-12-31"
    )

    print(f"=== 调试股票 {test_stock} ===")
    print(f"数据条数: {len(data)}")
    print(f"数据范围: {data['date'].min()} 到 {data['date'].max()}")

    if data.empty:
        print("数据为空")
        return

    # 显示数据样本
    print("\n数据样本:")
    print(data[['date', 'open', 'high', 'low', 'close', 'volume']].head(3))

    # 计算因子得分
    print("\n=== 计算因子得分 ===")

    # 动量强度因子 (LWR)
    lwr_period = 14
    high = data['high'].rolling(lwr_period).max()
    low = data['low'].rolling(lwr_period).min()
    close = data['close']

    # 避免除零
    denominator = high - low
    denominator = denominator.replace(0, np.nan)

    lwr = -100 * (high - close) / denominator
    momentum_scores = lwr.fillna(-50.0)

    print(f"LWR计算完成，数据长度: {len(momentum_scores)}")
    print(f"LWR样本: {momentum_scores.head(5).tolist()}")

    # 成交量激增因子
    volume_ma20 = data['volume'].rolling(window=20).mean()
    volume_ma20 = volume_ma20.replace(0, np.nan)

    volume_ratio = data['volume'] / volume_ma20
    volume_scores = volume_ratio.fillna(1.0)

    print(f"成交量比率计算完成，数据长度: {len(volume_scores)}")
    print(f"成交量比率样本: {volume_scores.head(5).tolist()}")

    # 标准化
    def normalize_scores(scores):
        if scores.empty:
            return scores

        # 滚动标准化
        rolling_mean = scores.rolling(window=252, min_periods=60).mean()
        rolling_std = scores.rolling(window=252, min_periods=60).std()
        rolling_std = rolling_std.replace(0, 1e-8)

        normalized = (scores - rolling_mean) / rolling_std

        # 映射到0-1
        min_val = normalized.min()
        max_val = normalized.max()

        if max_val > min_val:
            final_normalized = (normalized - min_val) / (max_val - min_val)
        else:
            final_normalized = pd.Series(0.5, index=normalized.index)

        return final_normalized.fillna(0.5)

    momentum_normalized = normalize_scores(momentum_scores)
    volume_normalized = normalize_scores(volume_scores)

    print(f"标准化后动量因子长度: {len(momentum_normalized)}")
    print(f"标准化后成交量因子长度: {len(volume_normalized)}")

    # 组合得分
    momentum_weight = 0.70
    volume_weight = 0.30

    combined_scores = (momentum_normalized * momentum_weight) + (volume_normalized * volume_weight)

    print(f"组合得分长度: {len(combined_scores)}")
    print(f"组合得分样本: {combined_scores.head(5).tolist()}")

    # 计算收益率
    returns = data['close'].pct_change().dropna()
    print(f"收益率长度: {len(returns)}")
    print(f"收益率样本: {returns.head(5).tolist()}")

    # 对齐数据
    print("\n=== 数据对齐 ===")
    aligned_data = pd.concat([combined_scores, returns], axis=1).dropna()
    print(f"对齐后数据长度: {len(aligned_data)}")

    if len(aligned_data) < 10:
        print("对齐后数据不足")
        return

    aligned_scores = aligned_data.iloc[:, 0]
    aligned_returns = aligned_data.iloc[:, 1]

    # 计算策略表现
    print("\n=== 计算策略表现 ===")

    # 分位数
    factor_quantile = aligned_scores.rank(pct=True)
    buy_signal = factor_quantile > 0.8

    print(f"买入信号数量: {buy_signal.sum()}")
    print(f"总信号数量: {len(buy_signal)}")
    print(f"选股比例: {buy_signal.mean():.2%}")

    strategy_returns = aligned_returns[buy_signal]
    print(f"策略收益数量: {len(strategy_returns)}")

    if len(strategy_returns) == 0:
        print("没有策略收益数据")
        return

    # 计算关键指标
    total_return = (1 + strategy_returns).prod() - 1
    trading_days = len(strategy_returns)
    annual_return = (1 + total_return) ** (252 / trading_days) - 1

    # 夏普比率
    excess_returns = strategy_returns - 0.03/252
    if excess_returns.std() > 0:
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    else:
        sharpe_ratio = 0

    # 最大回撤
    cumulative = (1 + strategy_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    # 胜率
    win_rate = (strategy_returns > 0).mean()

    # 信息比率
    market_returns = aligned_returns
    excess_returns_strategy = strategy_returns - market_returns.reindex(strategy_returns.index, fill_value=0)
    if excess_returns_strategy.std() > 0:
        information_ratio = excess_returns_strategy.mean() / excess_returns_strategy.std() * np.sqrt(252)
    else:
        information_ratio = 0

    # 输出结果
    print(f"\n=== {test_stock} 策略性能指标 ===")
    print(f"年化收益率: {annual_return:.2%}")
    print(f"夏普比率: {sharpe_ratio:.2f}")
    print(f"最大回撤: {max_drawdown:.2%}")
    print(f"胜率: {win_rate:.2%}")
    print(f"信息比率: {information_ratio:.2f}")
    print(f"总交易次数: {len(strategy_returns)}")
    print(f"交易天数: {trading_days}")

    return {
        'annual_return': annual_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'information_ratio': information_ratio,
        'total_trades': len(strategy_returns),
        'trading_days': trading_days,
        'selection_rate': len(strategy_returns) / len(aligned_returns)
    }

if __name__ == "__main__":
    debug_single_stock()