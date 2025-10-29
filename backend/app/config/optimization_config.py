#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
优化器最佳参数配置与预设策略
基于 optimization_20251019_202428 优化结果
"""

import logging
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 均值回归策略优化结果（生产可用）
MEAN_REVERSION_OPTIMIZATION: Dict[str, Any] = {
    "optimization_date": "2025-10-19T20:24:28",
    "total_combinations": 64,
    "successful_tests": 64,
    "test_period": "2022-01-01 to 2023-12-31",
    "best_parameters": {
        "lookback_period": 20,
        "buy_threshold": -0.08,
        "sell_threshold": 0.02,
    },
    "performance_metrics": {
        "total_return": 0.25426360801000053,  # 25.43%
        "sharpe_ratio": 1.2847362368806956,
        "max_drawdown": 0.3707833310568292,  # 37.08%
        "trade_count": 15,
        "composite_score": 7.885966198276808,
    },
    "stock_pool": ["000001", "000002", "600036", "600519", "000858"],
    "rebalancing_freq": 10,
}

# 统一导出供服务层使用
OPTIMIZATION_RESULTS = MEAN_REVERSION_OPTIMIZATION

# 动量策略优化结果（占位，待真实实验数据覆盖）
MOMENTUM_OPTIMIZATION: Dict[str, Any] = {
    "optimization_date": "pending",
    "total_combinations": 1024,
    "successful_tests": 0,
    "test_period": "2022-01-01 to 2023-12-31",
    "best_parameters": {
        "momentum_period": 10,
        "buy_threshold": 0.05,
        "sell_threshold": -0.03,
        "profit_target": 0.08,
        "max_hold_days": 20,
    },
    "performance_metrics": {
        "total_return": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "trade_count": 0,
        "composite_score": 0.0,
    },
    "stock_pool": ["000001", "000002", "600036", "600519", "000858"],
    "rebalancing_freq": 10,
    "status": "pending_optimization",
}

# 预设策略配置
PRESET_STRATEGIES: Dict[str, Dict[str, Any]] = {
    # 均值回归策略系列
    "conservative": {
        "name": "保守型均值回归策略",
        "strategy_type": "mean_reversion",
        "parameters": {
            "lookback_period": 20,
            "buy_threshold": -0.10,  # 更保守的买入阈值
            "sell_threshold": 0.02,
        },
        "risk_level": "low",
        "expected_return": "15-20%",
        "description": "保守型均值回归策略，追求稳定收益，风险较低",
    },
    "balanced": {
        "name": "平衡型均值回归策略",
        "strategy_type": "mean_reversion",
        "parameters": {
            "lookback_period": 20,
            "buy_threshold": -0.08,  # 最佳参数
            "sell_threshold": 0.02,
        },
        "risk_level": "medium",
        "expected_return": "20-25%",
        "description": "平衡型均值回归策略，基于优化器最佳参数配置",
    },
    "aggressive": {
        "name": "激进型均值回归策略",
        "strategy_type": "mean_reversion",
        "parameters": {
            "lookback_period": 15,  # 更短的回看期
            "buy_threshold": -0.05,  # 更激进的买入阈值
            "sell_threshold": 0.03,
        },
        "risk_level": "high",
        "expected_return": "25-30%",
        "description": "激进型均值回归策略，追求高收益，风险较高",
    },
    # 动量策略系列（基于经验参数，待优化）
    "momentum_conservative": {
        "name": "保守型动量策略",
        "strategy_type": "momentum",
        "parameters": {
            "momentum_period": 15,
            "buy_threshold": 0.08,  # 较高的买入阈值
            "sell_threshold": -0.05,  # 较保守的止损
            "profit_target": 0.06,  # 较保守的盈利目标
            "max_hold_days": 25,
        },
        "risk_level": "medium",
        "expected_return": "18-23%",
        "description": "保守型动量策略，追求趋势收益，中等风险",
        "status": "pending_optimization",
    },
    "momentum_balanced": {
        "name": "平衡型动量策略",
        "strategy_type": "momentum",
        "parameters": {
            "momentum_period": 10,
            "buy_threshold": 0.05,  # 适中的买入阈值
            "sell_threshold": -0.03,  # 适中的止损
            "profit_target": 0.08,  # 适中的盈利目标
            "max_hold_days": 20,
        },
        "risk_level": "medium-high",
        "expected_return": "22-28%",
        "description": "平衡型动量策略，平衡收益与风险",
        "status": "pending_optimization",
    },
    "momentum_aggressive": {
        "name": "激进型动量策略",
        "strategy_type": "momentum",
        "parameters": {
            "momentum_period": 5,  # 短期动量
            "buy_threshold": 0.03,  # 较低的买入阈值
            "sell_threshold": -0.02,  # 较宽松的止损
            "profit_target": 0.12,  # 较高的盈利目标
            "max_hold_days": 15,
        },
        "risk_level": "high",
        "expected_return": "25-35%",
        "description": "激进型动量策略，追求高趋势收益",
        "status": "pending_optimization",
    },
}

# 默认策略配置模板（使用均值回归优化器最佳参数）
DEFAULT_STRATEGY_TEMPLATE: Dict[str, Any] = {
    "name": "默认均值回归策略",
    "strategy_type": "mean_reversion",
    "parameters": MEAN_REVERSION_OPTIMIZATION["best_parameters"],
    "stock_pool": MEAN_REVERSION_OPTIMIZATION["stock_pool"],
    "rebalance_frequency": MEAN_REVERSION_OPTIMIZATION["rebalancing_freq"],
    "risk_level": "medium",
    "created_at": None,
    "optimization_based": True,
    "optimization_date": MEAN_REVERSION_OPTIMIZATION["optimization_date"],
    "expected_performance": MEAN_REVERSION_OPTIMIZATION["performance_metrics"],
}


def get_best_parameters(strategy_type: str = "mean_reversion") -> Dict[str, Any]:
    """获取优化器最佳参数"""
    if strategy_type == "mean_reversion":
        return deepcopy(MEAN_REVERSION_OPTIMIZATION["best_parameters"])
    if strategy_type == "momentum":
        return deepcopy(MOMENTUM_OPTIMIZATION["best_parameters"])

    logger.warning("未知的策略类型 %s，返回均值回归参数", strategy_type)
    return deepcopy(MEAN_REVERSION_OPTIMIZATION["best_parameters"])


def get_preset_strategy(preset_type: str) -> Dict[str, Any]:
    """获取预设策略配置"""
    preset = PRESET_STRATEGIES.get(preset_type, PRESET_STRATEGIES["balanced"])
    return deepcopy(preset)


def get_default_config() -> Dict[str, Any]:
    """获取默认策略配置"""
    config = deepcopy(DEFAULT_STRATEGY_TEMPLATE)
    config["created_at"] = datetime.now().isoformat()
    config["parameters"] = deepcopy(MEAN_REVERSION_OPTIMIZATION["best_parameters"])
    config["stock_pool"] = list(MEAN_REVERSION_OPTIMIZATION["stock_pool"])
    config["expected_performance"] = deepcopy(MEAN_REVERSION_OPTIMIZATION["performance_metrics"])
    return config


def validate_parameters(parameters: Dict[str, Any], strategy_type: str = "mean_reversion") -> bool:
    """验证参数是否在优化范围内"""
    if strategy_type == "mean_reversion":
        valid_ranges = {
            "lookback_period": [5, 10, 15, 20],
            "buy_threshold": [-0.03, -0.05, -0.08, -0.10],
            "sell_threshold": [0.02, 0.03, 0.05, 0.06],
        }
    elif strategy_type == "momentum":
        valid_ranges = {
            "momentum_period": [5, 10, 15, 20],
            "buy_threshold": [0.03, 0.05, 0.08, 0.10],
            "sell_threshold": [-0.02, -0.03, -0.05, -0.08],
            "profit_target": [0.05, 0.08, 0.10, 0.15],
            "max_hold_days": [10, 15, 20, 25],
        }
    else:
        logger.warning("未知的策略类型 %s", strategy_type)
        return False

    for param, value in parameters.items():
        if param in valid_ranges and value not in valid_ranges[param]:
            logger.warning("参数 %s=%s 不在优化测试范围内", param, value)
            return False
    return True


def update_momentum_optimization_results(optimization_results: Dict[str, Any]) -> None:
    """更新动量策略优化结果"""
    global MOMENTUM_OPTIMIZATION  # pylint: disable=global-statement
    MOMENTUM_OPTIMIZATION = deepcopy(optimization_results)
    logger.info("动量策略优化结果已更新")


if __name__ == "__main__":
    # 简单的自检输出
    print("=== 多策略优化器配置测试 ===")
    print(f"均值回归最佳参数: {get_best_parameters('mean_reversion')}")
    print(f"动量策略参数: {get_best_parameters('momentum')}")
    print(f"平衡型均值回归策略: {get_preset_strategy('balanced')}")
    print(f"平衡型动量策略: {get_preset_strategy('momentum_balanced')}")
