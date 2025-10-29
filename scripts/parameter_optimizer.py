#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter Optimizer (Engine-integrated)

基于无前视偏差回测引擎（Bias-Free Backtest Engine）的参数优化器。
提供稳健接口：ParameterOptimizationRunner.run_optimization(config, args)

config 示例：
{
  "strategy_name": "OptimizedMeanReversion",
  "parameter_grid": {
    "lookback_period": [5,10,20],
    "buy_threshold": [-0.03,-0.05],
    "sell_threshold": [0.02,0.03]
  },
  "fixed_parameters": {"max_hold_days": 15},
  "costs": {"commission": 0.0003, "stamp_duty": 0.001, "slippage": 0.001},
  "min_trades": 5
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import logging

from scripts.bias_free_backtest_engine import BiasFreeBacktestEngine
from scripts.parameter_optimization_engine import OptimizedMeanReversionStrategy


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class _Args:
    start_date: str
    end_date: str
    stock_pool: str
    rebalancing_freq: int = 10
    data_dir: str | None = None
    output_dir: str | None = None
    verbose: bool = False
    quiet: bool = False


class ParameterOptimizationRunner:
    def __init__(self) -> None:
        pass

    def _iter_parameter_combinations(self, grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        keys = list(grid.keys())
        combos: List[Dict[str, Any]] = []
        if not keys:
            return combos

        def _dfs(i: int, cur: Dict[str, Any]):
            if i == len(keys):
                combos.append(dict(cur))
                return
            k = keys[i]
            for v in grid.get(k, []):
                cur[k] = v
                _dfs(i + 1, cur)
                cur.pop(k, None)

        _dfs(0, {})
        return combos

    def _score(self, metrics: Dict[str, Any]) -> float:
        # Calmar Ratio: 年化收益 / 最大回撤
        ann = float(metrics.get("annual_return", 0.0))
        mdd = float(metrics.get("max_drawdown", 0.0))
        eps = 1e-6
        return ann / max(mdd, eps)

    def run_optimization(self, config: Dict[str, Any], args: Any) -> Dict[str, Any]:
        grid = config.get("parameter_grid", {})
        fixed = config.get("fixed_parameters", {})
        costs = config.get("costs", {})
        min_trades = int(config.get("min_trades", 0))

        combos = self._iter_parameter_combinations(grid)
        stock_pool = [c.strip() for c in str(getattr(args, "stock_pool", "")).split(",") if c.strip()]
        start_date = getattr(args, "start_date", None)
        end_date = getattr(args, "end_date", None)
        if not stock_pool or not start_date or not end_date:
            raise ValueError("stock_pool/start_date/end_date 不能为空")

        all_results: List[Dict[str, Any]] = []
        best: Dict[str, Any] | None = None

        for idx, params in enumerate(combos, start=1):
            try:
                combined = {**fixed, **params}
                engine = BiasFreeBacktestEngine()
                # 覆盖成本与滑点（可选）
                try:
                    if costs:
                        if 'commission' in costs:
                            engine.execution_engine.commission_rate = float(costs['commission'])
                        if 'stamp_duty' in costs:
                            engine.execution_engine.stamp_duty_rate = float(costs['stamp_duty'])
                        if 'slippage' in costs:
                            engine.execution_engine.slippage_rate = float(costs['slippage'])
                except Exception as _e:
                    logger.warning("成本参数设置失败，使用默认: %s", _e)

                strategy = OptimizedMeanReversionStrategy(**combined)
                engine.add_signal_generator(strategy)
                result = engine.run_bias_free_backtest(stock_pool, start_date, end_date)
                metrics = result.get("performance_metrics", {})
                trades_count = len(result.get("trades", []))
                metrics = dict(metrics)
                metrics["trade_count"] = trades_count
                if trades_count < min_trades:
                    continue

                score = self._score(metrics)
                rec = {"parameters": combined, "metrics": metrics, "score": score}
                all_results.append(rec)
                if best is None or score > best.get("score", float("-inf")):
                    best = rec
                logger.info(
                    "[%d/%d] params=%s calmar=%.4f sharpe=%.3f mdd=%.3f ann=%.3f trades=%d",
                    idx,
                    len(combos),
                    params,
                    score,
                    float(metrics.get("sharpe_ratio", 0)),
                    float(metrics.get("max_drawdown", 0)),
                    float(metrics.get("annual_return", 0)),
                    trades_count,
                )
            except Exception as exc:
                logger.error("参数组合失败 %s: %s", params, exc)
                continue

        summary = {
            "total_combinations": len(combos),
            "successful_tests": len(all_results),
            "all_results": all_results,
        }
        return {"best_result": best or {}, "summary": summary}

