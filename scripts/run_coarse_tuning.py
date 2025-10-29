#!/usr/bin/env python3



# -*- coding: utf-8 -*-
"""
Coarse Tuning Runner (full engine)

鐩爣锛氬湪瀹屾暣鏃犲墠瑙嗗亸宸洖娴嬪紩鎿庝笅锛岃繘琛屽惈鎴愭湰/婊戠偣鐨勫弬鏁扮矖璋冿紙Calmar 浼樺厛锛夈€?"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

try:
    import akshare as ak
    AK = True
except Exception:
    AK = False


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
    df = df.rename(columns={'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','成交额':'amount'})
    df["date"] = pd.to_datetime(df["date"])
    df["stock_code"] = code
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
        f"# {tag} 缁撴灉鎽樿",
        "",
        f"鏃堕棿: {datetime.now().isoformat()}",
        "",
        f"鎬荤粍鍚? {result.get('summary',{}).get('total_combinations', 0)}",
        f"鎴愬姛娴嬭瘯: {result.get('summary',{}).get('successful_tests', 0)}",
        "",
    ]
    best = result.get("best_result") or {}
    if best:
        lines += [
            "## 鏈€浼樺弬鏁?,
            "",
            "```json",
            json.dumps(best.get("parameters", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## 鎸囨爣",
            "",
            "```json",
            json.dumps(best.get("metrics", {}), ensure_ascii=False, indent=2),
            "```",
        ]
    (outdir / f"{tag}_report.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Coarse tuning (full engine, Calmar target)")
    p.add_argument("--pool", type=str, default="000001,000002,600036,600519,000858,600000,601318,000333,002415,300750", help="鑲＄エ姹狅紝閫楀彿鍒嗛殧")
    p.add_argument("--train", type=str, default="2022-01-01,2023-12-31", help="璁粌鍖洪棿 璧?姝?)
    p.add_argument("--valid", type=str, default=f"2024-01-01,{date.today().isoformat()}", help="楠岃瘉鍖洪棿 璧?姝?)
    p.add_argument("--commission", type=float, default=0.0003, help="浣ｉ噾鐜?榛樿0.0003)")
    p.add_argument("--stamp-duty", dest="stamp_duty", type=float, default=0.001, help="鍗拌姳绋?榛樿0.001锛屽崠鍑烘敹鍙?")
    p.add_argument("--slippage", type=float, default=0.001, help="婊戠偣(榛樿0.001)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    pool = [c.strip() for c in args.pool.split(",") if c.strip()]
    train_start, train_end = [s.strip() for s in args.train.split(",")]
    valid_start, valid_end = [s.strip() for s in args.valid.split(",")]

    print("[coarse] 鍑嗗鏁版嵁: 瑕嗙洊璁粌+楠岃瘉鍖洪棿鈥?)
    ensure_data(pool, start=min(train_start, valid_start), end=max(train_end, valid_end))

    print("[coarse] 杩愯璁粌闆嗙矖璋冪綉鏍?瀹屾暣寮曟搸锛孋almar 鐩爣)鈥?)
    grid = {
        "lookback_period": [5, 10, 15, 20, 30, 40],
        "buy_threshold": [-0.02, -0.03, -0.05, -0.08, -0.10, -0.12],
        "sell_threshold": [0.01, 0.02, 0.03, 0.05, 0.06],
    }
    fixed = {"max_hold_days": 15}

    from scripts.parameter_optimizer import ParameterOptimizationRunner
    runner = ParameterOptimizationRunner()
    cfg = {
        "strategy_name": "OptimizedMeanReversion",
        "parameter_grid": grid,
        "fixed_parameters": fixed,
        "costs": {"commission": args.commission, "stamp_duty": args.stamp_duty, "slippage": args.slippage},
    }

    class _Args:
        def __init__(self, start: str, end: str, pool: List[str]):
            self.data_dir = str(DATA_ROOT)
            self.output_dir = str(OUT_ROOT)
            self.start_date = start
            self.end_date = end
            self.rebalancing_freq = 10
            self.stock_pool = ",".join(pool)

    train_res = runner.run_optimization(cfg, _Args(train_start, train_end, pool))

    print("[coarse] 浠ヨ缁冩渶浼樺弬鏁板湪楠岃瘉闆嗚瘎浼?瀹屾暣寮曟搸)鈥?)
    best = (train_res.get("best_result") or {}).get("parameters", {})
    if not best:
        print("[warn] 璁粌闆嗘湭寰楀埌鏈€浼樺弬鏁帮紝浣跨敤榛樿鍙傛暟杩涜楠岃瘉")
        best = {"lookback_period": 20, "buy_threshold": -0.08, "sell_threshold": 0.02}
    valid_grid = {k: [v] for k, v in best.items()}
    valid_res = runner.run_optimization({**cfg, "parameter_grid": valid_grid}, _Args(valid_start, valid_end, pool))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = OUT_ROOT / f"coarse_tuning_{ts}"
    write_report(outdir, "train", train_res)
    write_report(outdir, "valid", valid_res)
    print(f"[coarse] 瀹屾垚銆傛姤鍛婄洰褰? {outdir}")


if __name__ == "__main__":
    main()


