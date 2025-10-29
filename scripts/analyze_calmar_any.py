#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def find_latest_valid_dir(base: Path) -> Optional[Path]:
    candidates = []
    for d in base.rglob("*"):
        if not d.is_dir():
            continue
        tr = d / "train_results.json"
        va = d / "valid_results.json"
        if tr.exists() and va.exists():
            try:
                data = load_json(tr)
            except Exception:
                continue
            arr = (data.get("summary") or {}).get("all_results") or []
            # consider valid if we have at least one result
            if arr:
                # ensure at least one sample can compute calmar
                ok = False
                for r in arr:
                    m = (r.get("metrics") or {})
                    if compute_calmar(m) is not None:
                        ok = True
                        break
                if ok:
                    mtime = max(tr.stat().st_mtime, va.stat().st_mtime)
                    candidates.append((mtime, d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def compute_calmar(metrics: Dict[str, Any]) -> Optional[float]:
    mdd = metrics.get("max_drawdown")
    if mdd is None:
        return None
    # prefer annual_return; fallback to total_return
    ann = metrics.get("annual_return")
    if ann is None:
        ann = metrics.get("total_return")
    if ann is None:
        return None
    if mdd is None or mdd <= 0:
        # avoid div-by-zero; treat as invalid
        return None
    return float(ann) / float(mdd)


def top_by_calmar(results: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    enriched: List[Tuple[float, Dict[str, Any]]] = []
    for r in results:
        m = r.get("metrics") or {}
        c = compute_calmar(m)
        if c is None or math.isinf(c) or math.isnan(c):
            continue
        r2 = dict(r)
        r2["calmar"] = c
        enriched.append((c, r2))
    enriched.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in enriched[:n]]


def sensitivity(results: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Dict[Any, float]]:
    from collections import defaultdict
    import statistics as st

    buckets: Dict[str, Dict[Any, List[float]]] = {
        k: defaultdict(list) for k in keys
    }
    for r in results:
        p = r.get("parameters") or {}
        m = r.get("metrics") or {}
        c = compute_calmar(m)
        if c is None:
            continue
        for k in keys:
            if k in p:
                buckets[k][p[k]].append(c)
    out: Dict[str, Dict[Any, float]] = {}
    for k, mp in buckets.items():
        out[k] = {vk: round(st.mean(v), 4) for vk, v in mp.items() if v}
    return out


def scatter_pairs(results: List[Dict[str, Any]], limit: int = 1000) -> List[Tuple[float, float]]:
    pairs: List[Tuple[float, float]] = []
    for r in results:
        m = r.get("metrics") or {}
        mdd = m.get("max_drawdown")
        ret = m.get("annual_return")
        if ret is None:
            ret = m.get("total_return")
        if mdd is None or ret is None:
            continue
        pairs.append((float(ret), float(mdd)))
        if len(pairs) >= limit:
            break
    return pairs


def main() -> None:
    base = Path("optimization_results")
    if not base.exists():
        print("optimization_results 目录不存在。")
        return
    d = find_latest_valid_dir(base)
    if not d:
        print("未找到包含有效 all_results 的结果目录。")
        return
    tr = load_json(d / "train_results.json")
    va = load_json(d / "valid_results.json")
    t_all = (tr.get("summary") or {}).get("all_results") or []
    v_all = (va.get("summary") or {}).get("all_results") or []

    print(f"分析目录: {d}")
    print(f"训练样本数: {len(t_all)} | 验证样本数: {len(v_all)}")

    # Top Calmar frontier (train)
    top = top_by_calmar(t_all, 15)
    if not top:
        print("训练集无可计算 Calmar 的样本（可能全部回撤为0或缺少年化/总收益）。")
    else:
        print("\n== Calmar 前沿（Train Top 15）==")
        for i, r in enumerate(top, 1):
            p = r.get("parameters") or {}
            m = r.get("metrics") or {}
            print(
                f"{i:>2}. L={p.get('lookback_period')} B={p.get('buy_threshold')} S={p.get('sell_threshold')} "
                f"| Calmar={r.get('calmar'):.4f} Return={(m.get('annual_return', m.get('total_return', 0.0))):.4f} "
                f"MDD={m.get('max_drawdown', 0.0):.4f}"
            )

    # Scatter (return vs drawdown)
    pairs = scatter_pairs(t_all)
    if not pairs:
        print("\n收益-回撤散点：无可绘制样本。")
    else:
        rets = [p[0] for p in pairs]
        mdds = [p[1] for p in pairs]
        def q(xs, qv):
            xs2 = sorted(xs)
            idx = int((len(xs2)-1)*qv)
            return xs2[idx]
        print("\n== 收益-回撤散点（文本摘要）==")
        print(
            f"Return min/median/max: {min(rets):.4f} / {q(rets,0.5):.4f} / {max(rets):.4f}"
        )
        print(
            f"MDD    min/median/max: {min(mdds):.4f} / {q(mdds,0.5):.4f} / {max(mdds):.4f}"
        )
        # show a few low-drawdown and high-return points
        pairs_sorted = sorted(pairs, key=lambda x: (x[1], -x[0]))
        print("代表点(低回撤优先，显示前10)：")
        for i, (rtn, mdd) in enumerate(pairs_sorted[:10], 1):
            print(f"  {i:>2}. Return={rtn:.4f}, MDD={mdd:.4f}")

    # Sensitivity
    print("\n== 参数敏感性（按均值 Calmar）==")
    sens = sensitivity(t_all, ["lookback_period", "buy_threshold", "sell_threshold"])
    for k in ["lookback_period", "buy_threshold", "sell_threshold"]:
        vals = sens.get(k) or {}
        if not vals:
            print(f"{k}: 无法计算（缺指标或样本不足）")
            continue
        items = sorted(vals.items(), key=lambda x: x[0])
        line = ", ".join([f"{kv[0]}:{kv[1]:.4f}" for kv in items])
        print(f"{k}: {line}")

    # Validation overlay for the top-5 train params
    if top and v_all:
        print("\n== 验证集回放（Top-5 训练参数）==")
        from collections import defaultdict
        # index valid results by param tuple
        idx: Dict[Tuple[Any, Any, Any], Dict[str, Any]] = {}
        for r in v_all:
            p = r.get("parameters") or {}
            key = (p.get("lookback_period"), p.get("buy_threshold"), p.get("sell_threshold"))
            idx[key] = r
        for r in top[:5]:
            p = r.get("parameters") or {}
            key = (p.get("lookback_period"), p.get("buy_threshold"), p.get("sell_threshold"))
            vr = idx.get(key)
            if not vr:
                print(f"L={key[0]} B={key[1]} S={key[2]} | 验证缺少对应结果")
                continue
            vm = vr.get("metrics") or {}
            vcal = compute_calmar(vm)
            if vcal is None:
                print(f"L={key[0]} B={key[1]} S={key[2]} | 验证无法计算 Calmar")
            else:
                print(
                    f"L={key[0]} B={key[1]} S={key[2]} | Valid Calmar={vcal:.4f} Return={(vm.get('annual_return', vm.get('total_return', 0.0))):.4f} MDD={vm.get('max_drawdown', 0.0):.4f}"
                )


if __name__ == "__main__":
    main()
