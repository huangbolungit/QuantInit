#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测运行脚本 - 命令行工具
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.backtesting.engine import BacktestEngine


def main():
    parser = argparse.ArgumentParser(description="A股策略回测工具")
    parser.add_argument("--start-date", type=str, required=True, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, required=True, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--momentum-weight", type=float, default=0.5, help="动量因子权重")
    parser.add_argument("--value-weight", type=float, default=0.5, help="价值因子权重")
    parser.add_argument("--rebalance", choices=["daily", "weekly", "monthly"], default="weekly",
                       help="调仓频率")
    parser.add_argument("--initial-capital", type=float, default=1000000, help="初始资金")
    parser.add_argument("--data-dir", type=str, help="数据目录")
    parser.add_argument("--stocks", type=str, help="指定股票代码，逗号分隔（用于测试）")

    args = parser.parse_args()

    print("A股智能投顾助手 - 回测工具")
    print("=" * 50)

    # 验证因子权重
    total_weight = args.momentum_weight + args.value_weight
    if abs(total_weight - 1.0) > 0.001:
        print(f"错误: 因子权重总和必须等于1.0，当前为{total_weight}")
        sys.exit(1)

    # 创建回测引擎
    engine = BacktestEngine(args.data_dir)
    engine.initial_capital = args.initial_capital

    # 设置因子权重
    engine.set_factor_weights(args.momentum_weight, args.value_weight)

    # 处理股票池
    stock_universe = None
    if args.stocks:
        stock_universe = [s.strip() for s in args.stocks.split(",")]

    print(f"回测配置:")
    print(f"- 回测期间: {args.start_date} 到 {args.end_date}")
    print(f"- 初始资金: {args.initial_capital:,.0f}")
    print(f"- 因子权重: 动量 {args.momentum_weight:.1%}, 价值 {args.value_weight:.1%}")
    print(f"- 调仓频率: {args.rebalance}")
    if stock_universe:
        print(f"- 股票池: {', '.join(stock_universe)}")

    print()

    # 运行回测
    try:
        results = engine.run_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            stock_universe=stock_universe,
            rebalance_frequency=args.rebalance
        )

        # 生成报告
        report = engine.generate_report(results)
        print(report)

        # 保存结果
        output_dir = Path(__file__).parent.parent / "data" / "backtest_results"
        output_dir.mkdir(exist_ok=True)

        # 保存详细结果
        import json
        timestamp = args.start_date.replace("-", "") + "_to_" + args.end_date.replace("-", "")
        result_file = output_dir / f"backtest_{timestamp}.json"
        report_file = output_dir / f"report_{timestamp}.txt"

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"回测结果已保存:")
        print(f"- 详细数据: {result_file}")
        print(f"- 报告文件: {report_file}")

    except Exception as e:
        print(f"回测失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()