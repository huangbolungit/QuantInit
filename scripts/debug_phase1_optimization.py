#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试第一阶段参数优化 - 找出无交易问题的根本原因
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.stateless_strategy_adapter import StatelessMeanReversionStrategy
from scripts.bias_free_backtest_engine import BiasFreeBacktestEngine
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_single_strategy():
    """调试单个策略的执行"""
    logger.info("🔍 开始调试单个策略执行...")

    # 创建策略实例
    strategy = StatelessMeanReversionStrategy(
        lookback_period=10,
        buy_threshold=-0.05,
        sell_threshold=0.03,
        stop_loss_threshold=0.10,
        profit_target=0.08,
        max_hold_days=15,
        position_size=1000
    )

    logger.info(f"✅ 策略创建成功: {strategy.name}")

    # 创建回测引擎
    backtester = OptimizedStrategyBacktester("data/historical/stocks/complete_csi800/stocks")

    # 测试单只股票
    stock_pool = ['000001']
    start_date = "2022-01-01"
    end_date = "2022-12-31"

    logger.info(f"📊 测试股票池: {stock_pool}")
    logger.info(f"📅 测试期间: {start_date} 到 {end_date}")

    try:
        # 运行回测
        result = backtester.run_strategy_test(
            strategy,
            stock_pool,
            start_date,
            end_date,
            rebalance_frequency=10
        )

        logger.info("🎯 回测完成，分析结果...")

        # 分析结果
        trades = result.get('trades', [])
        metrics = result.get('performance_metrics', {})

        logger.info(f"📈 总交易数: {len(trades)}")
        logger.info(f"💰 总收益: {metrics.get('total_return', 0):.2%}")
        logger.info(f"📊 夏普比率: {metrics.get('sharpe_ratio', 0):.3f}")
        logger.info(f"📉 最大回撤: {metrics.get('max_drawdown', 0):.2%}")

        # 显示前5个交易
        if trades:
            logger.info("🔍 前5个交易记录:")
            for i, trade in enumerate(trades[:5]):
                logger.info(f"  {i+1}. {trade}")
        else:
            logger.warning("⚠️ 没有产生任何交易！")

            # 检查信号生成
            logger.info("🔍 检查信号生成过程...")
            # 这里需要深入调试信号生成逻辑

    except Exception as e:
        logger.error(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()

def debug_data_loading():
    """调试数据加载"""
    logger.info("🔍 开始调试数据加载...")

    # 创建回测引擎
    backtester = OptimizedStrategyBacktester("data/historical/stocks/complete_csi800/stocks")

    # 测试数据加载
    try:
        # 加载单只股票数据
        stock_code = "000001"
        stock_data = backtester.data_loader.load_stock_data(stock_code, "2022-01-01", "2022-12-31")

        logger.info(f"✅ {stock_code} 数据加载成功")
        logger.info(f"📊 数据行数: {len(stock_data)}")
        logger.info(f"📊 数据列: {list(stock_data.columns)}")
        logger.info(f"📅 数据范围: {stock_data['date'].min()} 到 {stock_data['date'].max()}")

        # 显示前几行数据
        logger.info("📊 前3行数据:")
        for i, row in stock_data.head(3).iterrows():
            logger.info(f"  {row['date']}: {row['close']}")

    except Exception as e:
        logger.error(f"❌ 数据加载失败: {e}")
        import traceback
        traceback.print_exc()

def debug_signal_generation():
    """调试信号生成"""
    logger.info("🔍 开始调试信号生成...")

    # 这里需要模拟回测引擎的信号生成过程
    # 由于我们需要DataSnapshot，我们需要创建一个完整的调试流程

    logger.info("⚠️ 信号生成调试需要更深入的集成测试")
    logger.info("📝 建议：检查回测引擎中的信号生成调用链")

if __name__ == "__main__":
    logger.info("🚀 启动第一阶段优化调试")

    # 调试数据加载
    debug_data_loading()

    print("\n" + "="*50 + "\n")

    # 调试单个策略
    debug_single_strategy()

    print("\n" + "="*50 + "\n")

    # 调试信号生成
    debug_signal_generation()

    logger.info("🏁 调试完成")