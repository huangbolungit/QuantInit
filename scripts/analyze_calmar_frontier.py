#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import statistics as st


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def top_calmar(res: Dict[str, Any], n: int = 10) -> List[Dict[str, Any]]:
    arr = res.get("summary", {}).get("all_results", [])
    arr = [r for r in arr if r.get("metrics")]
    arr.sort(key=lambda r: r.get("score", float("-inf")), reverse=True)
    return arr[:n]


def sensitivity(res: Dict[str, Any]) -> Dict[str, Dict[Any, float]]:
    arr = res.get("summary", {}).get("all_results", [])
    sL: Dict[Any, List[float]] = {}
    sB: Dict[Any, List[float]] = {}
    sS: Dict[Any, List[float]] = {}
    for r in arr:
        p = r.get("parameters", {})
        sc = r.get("score", 0.0)
        sL.setdefault(p.get("lookback_period"), []).append(sc)
        sB.setdefault(p.get("buy_threshold"), []).append(sc)
        sS.setdefault(p.get("sell_threshold"), []).append(sc)
    out = {
        "lookback_period": {k: round(st.mean(v), 4) for k, v in sL.items() if v},
        "buy_threshold": {k: round(st.mean(v), 4) for k, v in sB.items() if v},
        "sell_threshold": {k: round(st.mean(v), 4) for k, v in sS.items() if v},
    }
    return out


def scatter_buckets(res: Dict[str, Any]) -> List[Tuple[Tuple[int, int], int]]:
    import numpy as np

    arr = res.get("summary", {}).get("all_results", [])
    pairs = [
        (
            r.get("metrics", {}).get("max_drawdown", 0.0),
            r.get("metrics", {}).get("annual_return", 0.0),
        )
        for r in arr
    ]
    mx = max((p[0] for p in pairs), default=0.01)
    mn = min((p[1] for p in pairs), default=0.0)
    Mx = max((p[1] for p in pairs), default=0.0)
    xs = np.linspace(0, mx, 6)
    ys = np.linspace(mn, Mx, 6)
    from collections import Counter

    C: Counter = Counter()
    for mdd, ann in pairs:
        xi = sum(mdd > xs[i] for i in range(5))
        yi = sum(ann > ys[i] for i in range(5))
        C[(xi, yi)] += 1
    return sorted(C.items())


def main() -> None:
    base = Path("optimization_results")
    # pick latest coarse_tuning_full_* dir
    dirs = sorted([p for p in base.glob("coarse_tuning_full_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not dirs:
        print("No coarse_tuning_full_* directory found under optimization_results")
        return
    d = dirs[0]
    tr = load(d / "train_results.json")
    va = load(d / "valid_results.json")

    print(f"Analysis directory: {d}")

    print("\n== TOP 10 (Train, by Calmar) ==")
    for i, r in enumerate(top_calmar(tr, 10), 1):
        p = r.get("parameters", {})
        m = r.get("metrics", {})
        print(
            f"{i:>2}. L={p.get('lookback_period')} B={p.get('buy_threshold')} S={p.get('sell_threshold')} | "
            f"Calmar={r.get('score',0):.4f} Ann={m.get('annual_return',0):.4f} MDD={m.get('max_drawdown',0):.4f} Sharpe={m.get('sharpe_ratio',0):.3f}"
        )

    print("\n== Sensitivity (mean Calmar by value) ==")
    sv = sensitivity(tr)
    for dim in ["lookback_period", "buy_threshold", "sell_threshold"]:
        vals = sv.get(dim, {})
        for k in sorted(vals):
            print(f"{dim}[{k}]: {vals[k]:.4f}")

    print("\n== Return-Drawdown Scatter buckets (5x5) ==")
    for (xi, yi), cnt in scatter_buckets(tr):
        print(f"bucket({xi},{yi})={cnt}")

    # Validation snapshot
    print("\n== Validation (best param set replay) ==")
    best = (tr.get("best_result") or {}).get("parameters", {})
    vm = (va.get("best_result") or {}).get("metrics", {})
    if best and vm:
        print(
            f"BestParam L={best.get('lookback_period')} B={best.get('buy_threshold')} S={best.get('sell_threshold')} | "
            f"Ann={vm.get('annual_return',0):.4f} MDD={vm.get('max_drawdown',0):.4f} Sharpe={vm.get('sharpe_ratio',0):.3f} Calmar={(vm.get('annual_return',0)/(vm.get('max_drawdown',1e-6) or 1e-6)):.4f}"
        )
    else:
        print("Validation metrics not available or best param missing.")


if __name__ == "__main__":
    main()

