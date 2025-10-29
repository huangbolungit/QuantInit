#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight, internal optimizer stubs to decouple backend from scripts/.

Provides minimal interfaces used by StrategyEngine:
- OptimizedMeanReversionStrategy: constructable strategy holder
- ParameterOptimizationRunner: returns best parameters summary
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.config.optimization_config import OPTIMIZATION_RESULTS


@dataclass
class OptimizedMeanReversionStrategy:
    """Minimal strategy placeholder compatible with StrategyEngine.

    Accepts parameters like lookback_period, buy_threshold, sell_threshold, etc.
    """

    lookback_period: int = 20
    buy_threshold: float = -0.08
    sell_threshold: float = 0.02
    max_hold_days: int = 15

    def __init__(self, **params: Any) -> None:
        # Set known params with defaults
        self.lookback_period = int(params.get("lookback_period", self.lookback_period))
        self.buy_threshold = float(params.get("buy_threshold", self.buy_threshold))
        self.sell_threshold = float(params.get("sell_threshold", self.sell_threshold))
        self.max_hold_days = int(params.get("max_hold_days", self.max_hold_days))

        # keep raw for future extension
        self._raw_params: Dict[str, Any] = dict(params)


class ParameterOptimizationRunner:
    """Minimal optimizer stub returning preset best parameters and metrics."""

    def __init__(self) -> None:
        pass

    async def optimize_mean_reversion(
        self,
        parameter_grid: Dict[str, List[Any]] | None = None,
        stock_pool: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return a summary consistent with StrategyEngine expectations."""
        best = {
            "parameters": dict(OPTIMIZATION_RESULTS.get("best_parameters", {})),
            "score": OPTIMIZATION_RESULTS.get("performance_metrics", {}).get(
                "composite_score", 0.0
            ),
            "metrics": dict(OPTIMIZATION_RESULTS.get("performance_metrics", {})),
        }

        return {
            "best_result": best,
            "summary": {
                "optimization_date": OPTIMIZATION_RESULTS.get("optimization_date"),
                "total_combinations": OPTIMIZATION_RESULTS.get("total_combinations", 0),
                "successful_tests": OPTIMIZATION_RESULTS.get("successful_tests", 0),
                "all_results": [],
            },
        }

