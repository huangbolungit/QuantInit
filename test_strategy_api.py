#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试策略API
"""

import asyncio
import httpx
import json

async def test_strategy_api():
    """测试策略API功能"""

    # 创建HTTP客户端
    async with httpx.AsyncClient() as client:
        base_url = "http://127.0.0.1:8000"

        print("开始测试策略API")

        # 1. 测试获取策略列表
        print("\n1. 测试获取策略列表...")
        response = await client.get(f"{base_url}/api/strategies")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        # 2. 测试创建策略
        print("\n2. 测试创建策略...")
        strategy_data = {
            "name": "测试均值回归策略",
            "strategy_type": "mean_reversion",
            "parameters": {
                "lookback_period": 10,
                "buy_threshold": -0.05,
                "sell_threshold": 0.03,
                "max_hold_days": 15
            },
            "stock_pool": ["000001", "000002", "600036"],
            "rebalance_frequency": 10
        }

        response = await client.post(
            f"{base_url}/api/strategies",
            json=strategy_data
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

        if response.status_code == 200:
            strategy_id = response.json()["id"]
            print(f"策略创建成功，ID: {strategy_id}")

            # 3. 测试获取策略详情
            print(f"\n3. 测试获取策略详情...")
            response = await client.get(f"{base_url}/api/strategies/{strategy_id}")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")

            # 4. 测试生成信号
            print(f"\n4. 测试生成交易信号...")
            response = await client.post(f"{base_url}/api/strategies/{strategy_id}/signals")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")

            # 5. 测试获取性能指标
            print(f"\n5. 测试获取策略性能...")
            response = await client.get(f"{base_url}/api/strategies/{strategy_id}/performance")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")

        print("\n测试完成!")

if __name__ == "__main__":
    asyncio.run(test_strategy_api())