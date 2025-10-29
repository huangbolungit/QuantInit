#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Market regime parameter optimisation across all local stocks."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

from parameter_optimizer import ParameterOptimizationRunner

DATA_ROOT = Path('data/historical/stocks')
CONFIG_PATH = Path('config/params.json')
OUTPUT_ROOT = Path('optimization_results/regime_analysis')
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

REGIMES: Dict[str, Dict[str, str]] = {
    'bull_2020_2021': {
        'start_date': '2020-01-01',
        'end_date': '2021-12-31'
    },
    'bear_2022_2023': {
        'start_date': '2022-01-01',
        'end_date': '2023-12-31'
    }
}

REBALANCING_FREQS: List[int] = [5, 10, 20]


def load_parameter_config() -> Dict:
    with CONFIG_PATH.open('r', encoding='utf-8') as fh:
        return json.load(fh)


def collect_all_stock_codes(data_root: Path) -> List[str]:
    codes = set()
    base = data_root
    if (base / 'stocks').exists():
        base = base / 'stocks'
    for csv_file in base.rglob('*.csv'):
        codes.add(csv_file.stem)
    return sorted(codes)


def resolve_data_dir() -> Path:
    candidates = [
        DATA_ROOT / 'complete_csi800' / 'stocks',
        DATA_ROOT / 'complete_csi800',
        DATA_ROOT
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError('Unable to locate local stock data directory')


def run_regime_analysis():
    parameter_config = load_parameter_config()
    data_dir = resolve_data_dir()
    all_codes = collect_all_stock_codes(data_dir)

    combinations = (
        len(parameter_config['parameter_grid'].get('lookback_period', []))
        * len(parameter_config['parameter_grid'].get('buy_threshold', []))
        * len(parameter_config['parameter_grid'].get('sell_threshold', []))
    )

    summary_lines = [
        '# Market Regime Analysis Summary',
        '',
        f'- Stock universe size: {len(all_codes)}',
        f'- Parameter combinations: {combinations}',
        ''
    ]

    best_overall = []

    for regime_name, period in REGIMES.items():
        for freq in REBALANCING_FREQS:
            runner = ParameterOptimizationRunner()
            output_dir = OUTPUT_ROOT / regime_name / f"freq{freq}"
            output_dir.mkdir(parents=True, exist_ok=True)
            runner.output_dir = output_dir

            args = SimpleNamespace(
                data_dir=str(data_dir),
                output_dir=str(output_dir),
                start_date=period['start_date'],
                end_date=period['end_date'],
                rebalancing_freq=freq,
                stock_pool=','.join(all_codes),
                quiet=True,
                verbose=False
            )

            results = runner.run_optimization(parameter_config, args)
            runner.save_results(results, args)

            best = results.get('best_result')
            if best:
                best_overall.append((regime_name, freq, best))
                summary_lines.append(f"## {regime_name} | rebalance {freq}d")
                summary_lines.append('')
                summary_lines.append(f"- Best parameters: {best['parameters']}")
                summary_lines.append(f"- Total return: {best.get('total_return', 0) * 100:.2f}%")
                summary_lines.append(f"- Sharpe ratio: {best.get('sharpe_ratio', 0):.2f}")
                summary_lines.append(f"- Max drawdown: {best.get('max_drawdown', 0) * 100:.2f}%")
                summary_lines.append(f"- Trades: {best.get('trade_count', 0)}")
                summary_lines.append('')

    report_path = OUTPUT_ROOT / 'regime_summary.md'
    report_path.write_text('\n'.join(summary_lines), encoding='utf-8')

    if best_overall:
        best_overall.sort(key=lambda item: item[2].get('score', 0), reverse=True)
        top = best_overall[0]
        print('Top scoring configuration:')
        print(
            f"Regime={top[0]}, rebalance={top[1]}d, params={top[2]['parameters']}, "
            f"return={top[2].get('total_return', 0) * 100:.2f}%"
        )


if __name__ == '__main__':
    run_regime_analysis()
