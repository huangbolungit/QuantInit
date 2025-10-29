#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略引擎 - 核心交易功能集成
统一的策略管理和执行系统
"""

import asyncio
import logging
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace
import sys
import pandas as pd
import numpy as np

from app.services.backtesting.parameter_optimizer import (
    OptimizedMeanReversionStrategy,
    ParameterOptimizationRunner,
)
from app.services.data_acquisition.akshare_client import AkShareDataAcquirer
from app.config.optimization_config import (
    get_best_parameters,
    get_default_config,
    get_preset_strategy,
    validate_parameters,
    OPTIMIZATION_RESULTS,
    PRESET_STRATEGIES
)

logger = logging.getLogger(__name__)

class StrategyStatus(Enum):
    """策略状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class TradingSignal:
    """交易信号数据结构"""
    id: str
    strategy_id: str
    stock_code: str
    signal_type: SignalType
    confidence: float  # 0-1 信号置信度
    price: float
    timestamp: datetime
    reason: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_return: float = 0.0
    risk_level: str = "medium"  # low, medium, high

@dataclass
class StrategyConfig:
    """策略配置数据结构"""
    id: str
    name: str
    strategy_type: str  # mean_reversion, momentum, value, etc.
    parameters: Dict[str, Any]
    stock_pool: List[str]
    rebalance_frequency: int  # days
    status: StrategyStatus = StrategyStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_signal_time: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)

class StrategyEngine:
    """策略引擎 - 核心交易功能集成"""

    def __init__(self, data_dir: str = None):
        """
        初始化策略引擎

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir or "data/historical/stocks/complete_csi800/stocks"
        self.data_acquirer = AkShareDataAcquirer()
        self.parameter_optimizer = ParameterOptimizationRunner()

        # 策略管理
        self.active_strategies: Dict[str, StrategyConfig] = {}
        self.strategy_instances: Dict[str, Any] = {}  # 策略实例

        # 信号管理
        self.signal_history: List[TradingSignal] = []
        self.signal_callbacks: List[Callable] = []

        # 性能监控
        self.performance_tracker: Dict[str, Dict] = {}

        logger.info("策略引擎初始化完成")

    async def create_strategy(self,
                            name: str,
                            strategy_type: str,
                            parameters: Dict[str, Any],
                            stock_pool: List[str],
                            rebalance_frequency: int = 10) -> str:
        """
        创建新策略

        Args:
            name: 策略名称
            strategy_type: 策略类型
            parameters: 策略参数
            stock_pool: 股票池
            rebalance_frequency: 调频周期

        Returns:
            strategy_id: 策略ID
        """
        strategy_id = str(uuid.uuid4())

        # 创建策略配置
        config = StrategyConfig(
            id=strategy_id,
            name=name,
            strategy_type=strategy_type,
            parameters=parameters,
            stock_pool=stock_pool,
            rebalance_frequency=rebalance_frequency
        )

        # 创建策略实例
        try:
            if strategy_type == "mean_reversion":
                strategy_instance = OptimizedMeanReversionStrategy(**parameters)
            else:
                raise ValueError(f"不支持的策略类型: {strategy_type}")

            self.active_strategies[strategy_id] = config
            self.strategy_instances[strategy_id] = strategy_instance
            self.performance_tracker[strategy_id] = {
                "signals_generated": 0,
                "successful_trades": 0,
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "last_updated": datetime.now()
            }

            logger.info(f"策略创建成功: {name} (ID: {strategy_id})")
            return strategy_id

        except Exception as e:
            logger.error(f"策略创建失败: {e}")
            raise

    async def update_strategy(self,
                            strategy_id: str,
                            parameters: Dict[str, Any] = None,
                            stock_pool: List[str] = None,
                            status: StrategyStatus = None) -> bool:
        """
        更新策略配置

        Args:
            strategy_id: 策略ID
            parameters: 新参数
            stock_pool: 新股票池
            status: 新状态

        Returns:
            success: 是否更新成功
        """
        if strategy_id not in self.active_strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return False

        config = self.active_strategies[strategy_id]

        try:
            # 更新配置
            if parameters:
                config.parameters.update(parameters)
                # 重新创建策略实例
                if config.strategy_type == "mean_reversion":
                    self.strategy_instances[strategy_id] = OptimizedMeanReversionStrategy(**config.parameters)

            if stock_pool:
                config.stock_pool = stock_pool

            if status:
                config.status = status

            config.updated_at = datetime.now()

            logger.info(f"策略更新成功: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"策略更新失败: {e}")
            return False

    async def delete_strategy(self, strategy_id: str) -> bool:
        """
        删除策略

        Args:
            strategy_id: 策略ID

        Returns:
            success: 是否删除成功
        """
        if strategy_id not in self.active_strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return False

        try:
            del self.active_strategies[strategy_id]
            del self.strategy_instances[strategy_id]
            del self.performance_tracker[strategy_id]

            logger.info(f"策略删除成功: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"策略删除失败: {e}")
            return False

    async def generate_signals(self, strategy_id: str = None) -> List[TradingSignal]:
        """
        生成交易信号

        Args:
            strategy_id: 策略ID，如果为None则为所有活跃策略生成信号

        Returns:
            signals: 交易信号列表
        """
        signals = []

        # 确定要生成信号的策略
        target_strategies = [strategy_id] if strategy_id else list(self.active_strategies.keys())

        for sid in target_strategies:
            if sid not in self.active_strategies:
                continue

            config = self.active_strategies[sid]
            if config.status != StrategyStatus.ACTIVE:
                continue

            try:
                # 获取最新数据
                current_data = await self._get_current_data(config.stock_pool)

                # 生成信号
                strategy_signals = await self._generate_strategy_signals(sid, config, current_data)
                signals.extend(strategy_signals)

                # 更新性能指标
                self.performance_tracker[sid]["signals_generated"] += len(strategy_signals)
                self.performance_tracker[sid]["last_updated"] = datetime.now()
                config.last_signal_time = datetime.now()

            except Exception as e:
                logger.error(f"策略 {sid} 信号生成失败: {e}")
                continue

        # 保存信号历史
        self.signal_history.extend(signals)

        # 触发回调
        for callback in self.signal_callbacks:
            try:
                await callback(signals)
            except Exception as e:
                logger.error(f"信号回调执行失败: {e}")

        return signals

    async def _generate_strategy_signals(self,
                                       strategy_id: str,
                                       config: StrategyConfig,
                                       market_data: Dict[str, Any]) -> List[TradingSignal]:
        """
        为单个策略生成信号

        Args:
            strategy_id: 策略ID
            config: 策略配置
            market_data: 市场数据

        Returns:
            signals: 交易信号列表
        """
        signals = []
        strategy_instance = self.strategy_instances[strategy_id]

        # 创建数据快照 (适配回测引擎接口)
        from scripts.bias_free_backtest_engine import DataSnapshot, TradingInstruction

        # 这里需要根据实际策略接口进行调整
        # 由于OptimizedMeanReversionStrategy需要特定的数据格式，我们需要适配

        for stock_code, stock_info in market_data.items():
            try:
                # 简化的信号生成逻辑
                # 实际实现中需要根据策略的具体接口进行调整

                # 示例：基于均值的简单信号
                current_price = stock_info.get('current_price', 0)
                historical_prices = stock_info.get('historical_prices', [])

                if len(historical_prices) > 10:
                    mean_price = np.mean(historical_prices[-10:])
                    deviation = (current_price - mean_price) / mean_price

                    # 生成信号
                    if deviation < -0.05:  # 低于均值5%以上，买入信号
                        signal = TradingSignal(
                            id=str(uuid.uuid4()),
                            strategy_id=strategy_id,
                            stock_code=stock_code,
                            signal_type=SignalType.BUY,
                            confidence=min(abs(deviation) * 10, 1.0),
                            price=current_price,
                            timestamp=datetime.now(),
                            reason=f"均值回归信号: 偏离均值 {deviation:.3f}",
                            parameters=config.parameters.copy(),
                            expected_return=abs(deviation) * 100,
                            risk_level="medium"
                        )
                        signals.append(signal)

                    elif deviation > 0.03:  # 高于均值3%以上，卖出信号
                        signal = TradingSignal(
                            id=str(uuid.uuid4()),
                            strategy_id=strategy_id,
                            stock_code=stock_code,
                            signal_type=SignalType.SELL,
                            confidence=min(abs(deviation) * 10, 1.0),
                            price=current_price,
                            timestamp=datetime.now(),
                            reason=f"均值回归信号: 偏离均值 {deviation:.3f}",
                            parameters=config.parameters.copy(),
                            expected_return=abs(deviation) * 100,
                            risk_level="medium"
                        )
                        signals.append(signal)

            except Exception as e:
                logger.warning(f"股票 {stock_code} 信号生成失败: {e}")
                continue

        return signals

    async def _get_current_data(self, stock_pool: List[str]) -> Dict[str, Any]:
        """
        获取当前市场数据

        Args:
            stock_pool: 股票池

        Returns:
            market_data: 市场数据
        """
        market_data = {}

        for stock_code in stock_pool:
            try:
                # 获取实时数据 (这里简化处理)
                stock_data = await self.data_acquirer.get_stock_data(stock_code, days=30)

                if stock_data and not stock_data.empty:
                    latest_data = stock_data.iloc[-1]
                    market_data[stock_code] = {
                        'current_price': latest_data['close'],
                        'historical_prices': stock_data['close'].tolist(),
                        'volume': latest_data['volume'],
                        'timestamp': latest_data.name if hasattr(latest_data.name, 'strftime') else datetime.now()
                    }

            except Exception as e:
                logger.warning(f"获取股票 {stock_code} 数据失败: {e}")
                continue

        return market_data

    async def get_strategy_signals(self, strategy_id: str, limit: int = 100) -> List[TradingSignal]:
        """
        获取策略的历史信号

        Args:
            strategy_id: 策略ID
            limit: 返回信号数量限制

        Returns:
            signals: 信号列表
        """
        strategy_signals = [s for s in self.signal_history if s.strategy_id == strategy_id]
        return sorted(strategy_signals, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_active_strategies(self) -> List[StrategyConfig]:
        """
        获取所有活跃策略

        Returns:
            strategies: 策略配置列表
        """
        return [config for config in self.active_strategies.values() if config.status == StrategyStatus.ACTIVE]

    async def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略性能指标

        Args:
            strategy_id: 策略ID

        Returns:
            performance: 性能指标
        """
        if strategy_id not in self.performance_tracker:
            return {}

        performance = self.performance_tracker[strategy_id].copy()

        # 计算额外指标
        strategy_signals = [s for s in self.signal_history if s.strategy_id == strategy_id]

        if strategy_signals:
            buy_signals = [s for s in strategy_signals if s.signal_type == SignalType.BUY]
            sell_signals = [s for s in strategy_signals if s.signal_type == SignalType.SELL]

            performance.update({
                "total_signals": len(strategy_signals),
                "buy_signals": len(buy_signals),
                "sell_signals": len(sell_signals),
                "signal_quality": np.mean([s.confidence for s in strategy_signals]) if strategy_signals else 0,
                "last_signal_time": max([s.timestamp for s in strategy_signals]).isoformat() if strategy_signals else None
            })

        return performance

    def add_signal_callback(self, callback: Callable):
        """
        添加信号回调函数

        Args:
            callback: 回调函数，接受信号列表作为参数
        """
        self.signal_callbacks.append(callback)

    def remove_signal_callback(self, callback: Callable):
        """
        移除信号回调函数

        Args:
            callback: 要移除的回调函数
        """
        if callback in self.signal_callbacks:
            self.signal_callbacks.remove(callback)

    async def optimize_strategy_parameters(self,
                                         strategy_id: str,
                                         optimization_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化策略参数

        Args:
            strategy_id: 策略ID
            optimization_config: 优化配置

        Returns:
            optimization_result: 优化结果
        """
        if strategy_id not in self.active_strategies:
            raise ValueError(f"策略不存在: {strategy_id}")

        config = self.active_strategies[strategy_id]

        try:
            param_grid = optimization_config.get('parameter_grid', {})
            if not param_grid:
                return {"error": "参数网格不能为空"}

            strategy_name_map = {
                "mean_reversion": "OptimizedMeanReversion",
                "momentum": "SimpleMomentum"
            }

            runner_strategy = optimization_config.get('strategy_name') or strategy_name_map.get(config.strategy_type)
            if runner_strategy is None:
                return {"error": f"暂不支持策略类型: {config.strategy_type}"}

            fixed_parameters = dict(optimization_config.get('fixed_parameters', {}))
            for key, value in config.parameters.items():
                if key not in param_grid and key not in fixed_parameters:
                    fixed_parameters[key] = value

            stock_pool_source = optimization_config.get('stock_pool', config.stock_pool)
            if isinstance(stock_pool_source, str):
                stock_pool_list = [code.strip() for code in stock_pool_source.split(',') if code.strip()]
            else:
                stock_pool_list = [str(code).strip() for code in stock_pool_source]

            if not stock_pool_list:
                stock_pool_list = list(self.parameter_optimizer.default_config.get('stock_pool', []))

            defaults = self.parameter_optimizer.default_config
            start_date = optimization_config.get('start_date', defaults.get('start_date'))
            end_date = optimization_config.get('end_date', defaults.get('end_date'))
            rebalance_frequency = int(optimization_config.get('rebalancing_freq', config.rebalance_frequency or defaults.get('rebalancing_freq', 10)))
            data_dir = optimization_config.get('data_dir', defaults.get('data_dir'))

            runner_args = SimpleNamespace(
                start_date=start_date,
                end_date=end_date,
                rebalancing_freq=rebalance_frequency,
                stock_pool=",".join(stock_pool_list),
                data_dir=data_dir,
                quiet=optimization_config.get('quiet', True),
                verbose=optimization_config.get('verbose', False)
            )

            runner_config = {
                "strategy_name": runner_strategy,
                "parameter_grid": {key: list(values) for key, values in param_grid.items()},
                "fixed_parameters": fixed_parameters
            }

            loop = asyncio.get_running_loop()

            def _execute_run():
                return self.parameter_optimizer.run_optimization(runner_config, runner_args)

            optimization_summary = await loop.run_in_executor(None, _execute_run)
            best_result = optimization_summary.get("best_result")

            if not best_result or 'error' in best_result:
                logger.warning("策略 %s 优化未找到有效组合", strategy_id)
                return {
                    "error": "未找到有效的参数组合",
                    "summary": optimization_summary
                }

            best_parameters = best_result.get("parameters", {})
            optimization_score = best_result.get("score", 0.0)

            logger.info(
                "策略 %s 参数优化完成，总组合 %s，最佳得分 %.3f",
                strategy_id,
                optimization_summary.get("total_combinations"),
                optimization_score
            )

            return {
                "strategy_id": strategy_id,
                "best_parameters": best_parameters,
                "optimization_score": optimization_score,
                "total_combinations": optimization_summary.get("total_combinations"),
                "successful_tests": optimization_summary.get("successful_tests"),
                "optimization_time": optimization_summary.get("optimization_date"),
                "best_result": best_result,
                "all_results": optimization_summary.get("all_results", [])
            }

        except Exception as e:
            logger.error(f"策略参数优化失败: {e}")
            return {"error": str(e)}

    async def cleanup_old_signals(self, days_to_keep: int = 30):
        """
        清理旧的信号数据

        Args:
            days_to_keep: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        original_count = len(self.signal_history)
        self.signal_history = [s for s in self.signal_history if s.timestamp > cutoff_date]

        removed_count = original_count - len(self.signal_history)
        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 个旧信号，保留 {len(self.signal_history)} 个信号")

    async def create_optimized_strategy(self,
                                      preset_type: str = "balanced",
                                      custom_name: str = None) -> str:
        """
        创建基于优化器最佳参数的策略

        Args:
            preset_type: 预设类型 ("conservative", "balanced", "aggressive")
            custom_name: 自定义策略名称

        Returns:
            strategy_id: 策略ID
        """
        try:
            # 获取预设配置
            preset_config = get_preset_strategy(preset_type)

            # 生成策略名称
            strategy_name = custom_name or preset_config["name"]

            # 创建基于优化器的策略
            strategy_id = await self.create_strategy(
                name=strategy_name,
                strategy_type="mean_reversion",
                parameters=preset_config["parameters"],
                stock_pool=list(OPTIMIZATION_RESULTS["stock_pool"]),
                rebalance_frequency=OPTIMIZATION_RESULTS["rebalancing_freq"]
            )

            # 添加优化器元数据
            config = self.active_strategies[strategy_id]
            config.performance_metrics.update({
                "optimization_based": True,
                "optimization_date": OPTIMIZATION_RESULTS["optimization_date"],
                "expected_performance": deepcopy(OPTIMIZATION_RESULTS["performance_metrics"]),
                "risk_level": preset_config["risk_level"],
                "expected_return": preset_config["expected_return"],
                "description": preset_config["description"]
            })

            logger.info(f"创建优化器策略成功: {strategy_name} (ID: {strategy_id})")
            return strategy_id

        except Exception as e:
            logger.error(f"创建优化器策略失败: {e}")
            raise

    def get_optimization_info(self) -> Dict[str, Any]:
        """获取优化器信息"""
        return {
            "optimization_results": deepcopy(OPTIMIZATION_RESULTS),
            "available_presets": list(PRESET_STRATEGIES.keys()),
            "best_parameters": get_best_parameters(),
            "default_config": get_default_config()
        }

    def validate_strategy_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证策略参数并提供建议"""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "suggestions": []
        }

        # 检查参数是否在优化测试范围内
        if not validate_parameters(parameters):
            validation_result["is_valid"] = False
            validation_result["warnings"].append("参数不在优化测试范围内")
            validation_result["suggestions"].append(f"建议使用最佳参数: {get_best_parameters()}")

        # 与最佳参数对比
        best_params = get_best_parameters()
        for param, value in parameters.items():
            if param in best_params and value != best_params[param]:
                validation_result["warnings"].append(f"{param} 与最佳参数不同 ({value} vs {best_params[param]})")

        return validation_result

# 全局策略引擎实例
strategy_engine = None

def get_strategy_engine() -> StrategyEngine:
    """获取全局策略引擎实例"""
    global strategy_engine
    if strategy_engine is None:
        strategy_engine = StrategyEngine()
    return strategy_engine
