#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any
import sys

import pandas as pd

try:
    import akshare as ak
    AK = True
except Exception:
    AK = False

# ensure repo root on sys.path for `scripts.*` imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

DATA_ROOT = Path("data/historical/stocks/complete_csi800/stocks")
OUT_ROOT = Path("optimization_results")
OUT_ROOT.mkdir(parents=True, exist_ok=True)


def fetch_and_store(code: str, start: str, end: str) -> int:
    if not AK:
        return 0
    df = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start.replace("-", ""),
        end_date=end.replace("-", ""),
        adjust="qfq",
    )
    if df is None or df.empty:
        return 0
    # normalize columns (avoid non-ascii literals)
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df.iloc[:, 0])
    out["open"] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    out["close"] = pd.to_numeric(df.iloc[:, 2], errors="coerce")
    out["high"] = pd.to_numeric(df.iloc[:, 3], errors="coerce")
    out["low"] = pd.to_numeric(df.iloc[:, 4], errors="coerce")
    out["volume"] = pd.to_numeric(df.iloc[:, 5], errors="coerce") if df.shape[1] > 5 else 0
    out["amount"] = pd.to_numeric(df.iloc[:, 6], errors="coerce") if df.shape[1] > 6 else 0
    df = out
    total = 0
    for y, g in df.groupby(df["date"].dt.year):
        ydir = DATA_ROOT / str(y)
        ydir.mkdir(parents=True, exist_ok=True)
        fp = ydir / f"{code}.csv"
        if fp.exists():
            old = pd.read_csv(fp)
            old["date"] = pd.to_datetime(old["date"])
            merged = pd.concat([old, g], ignore_index=True)
            merged = merged.drop_duplicates(subset=["date"]).sort_values("date")
            merged.to_csv(fp, index=False)
            total += len(g)
        else:
            g.to_csv(fp, index=False)
            total += len(g)
    return total


def ensure_data(pool: List[str], start: str, end: str) -> None:
    for code in pool:
        try:
            cnt = fetch_and_store(code, start, end)
            print(f"[data] {code}: +{cnt} rows")
        except Exception as e:
            print(f"[data] {code}: failed {e}")


def write_report(outdir: Path, tag: str, result: Dict[str, Any]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{tag}_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# {tag} Summary",
        "",
        f"Time: {datetime.now().isoformat()}",
        "",
        f"Total combos: {result.get('summary',{}).get('total_combinations', 0)}",
        f"Successful: {result.get('summary',{}).get('successful_tests', 0)}",
        "",
    ]
    best = result.get("best_result") or {}
    if best:
        lines += [
            "## Best Parameters",
            "",
            "```json",
            json.dumps(best.get("parameters", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## Metrics",
            "",
            "```json",
            json.dumps(best.get("metrics", {}), ensure_ascii=False, indent=2),
            "```",
        ]
    (outdir / f"{tag}_report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Coarse tuning (full engine, Calmar target)")
    p.add_argument(
        "--pool",
        type=str,
        default="000001,000002,600036,600519,000858,600000,601318,000333,002415,300750",
        help="Stock pool, comma separated",
    )
    p.add_argument(
        "--train",
        type=str,
        default="2022-01-01,2023-12-31",
        help="Train range start,end",
    )
    p.add_argument(
        "--valid",
        type=str,
        default=f"2024-01-01,{date.today().isoformat()}",
        help="Valid range start,end",
    )
    p.add_argument("--commission", type=float, default=0.0003, help="Commission")
    p.add_argument(
        "--stamp-duty", dest="stamp_duty", type=float, default=0.001, help="Stamp duty (sell)"
    )
    p.add_argument("--slippage", type=float, default=0.001, help="Slippage")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pool = [c.strip() for c in args.pool.split(",") if c.strip()]
    train_start, train_end = [s.strip() for s in args.train.split(",")]
    valid_start, valid_end = [s.strip() for s in args.valid.split(",")]

    print("[coarse] Preparing data...")
    ensure_data(pool, start=min(train_start, valid_start), end=max(train_end, valid_end))

    print("[coarse] Running train grid (full engine, Calmar)...")
    # Expanded grid to increase triggers (per plan)
    grid = {
        "lookback_period": [5, 10, 20],
        "buy_threshold": [-0.005, -0.008, -0.015, -0.02, -0.03],
        "sell_threshold": [0.005, 0.01, 0.02],
    }
    fixed = {"max_hold_days": 30}

    from scripts.parameter_optimizer import ParameterOptimizationRunner

    runner = ParameterOptimizationRunner()
    cfg = {
        "strategy_name": "OptimizedMeanReversion",
        "parameter_grid": grid,
        "fixed_parameters": fixed,
        "costs": {
            "commission": args.commission,
            "stamp_duty": args.stamp_duty,
            "slippage": args.slippage,
        },
        "min_trades": 1,
    }

    class _Args:
        def __init__(self, start: str, end: str, pool: List[str]):
            self.data_dir = str(DATA_ROOT)
            self.output_dir = str(OUT_ROOT)
            self.start_date = start
            self.end_date = end
            self.rebalancing_freq = 1
            self.stock_pool = ",".join(pool)

    train_res = runner.run_optimization(cfg, _Args(train_start, train_end, pool))

    print("[coarse] Evaluating best on validation...")
    best = (train_res.get("best_result") or {}).get("parameters", {})
    if not best:
        print("[warn] no best params from train; using fallback")
        best = {"lookback_period": 20, "buy_threshold": -0.08, "sell_threshold": 0.02}
    valid_grid = {k: [v] for k, v in best.items()}
    valid_res = runner.run_optimization({**cfg, "parameter_grid": valid_grid}, _Args(valid_start, valid_end, pool))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = OUT_ROOT / f"coarse_tuning_full_{ts}"
    write_report(outdir, "train", train_res)
    write_report(outdir, "valid", valid_res)
    print(f"[coarse] done. reports: {outdir}")


if __name__ == "__main__":
    main()
