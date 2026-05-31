from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
LAB_DIR = Path(os.environ.get("NATIVE_STRATEGY_LAB_DIR", str(ROOT / "data" / "research_state" / "native_strategy_lab")))
CATALOG_PATH = LAB_DIR / "catalog.json"
BATCH_RUNS_PATH = LAB_DIR / "batch_runs.json"
GENERATOR_RUNS_PATH = LAB_DIR / "generator_runs.json"

ENGINE_WARMUP_BARS = 60
FAST_FILTER_TAIL_BARS = 400
FAST_FILTER_TRADE_SAMPLE = 8

DEFAULT_PROMOTION_POLICY = {
    "min_trades": 5,
    "min_profit_factor": 1.05,
    "max_drawdown_pct": 35.0,
    "min_wfo_robustness": 0.30,
    "min_mc_prob_profit": 0.45,
    "min_score": 45.0,
    "min_mt5_correlation_score": 0.0,
    "min_win_rate": 0.40,
}

DEFAULT_SCORING_PROFILE = {
    "profit_factor_weight": 40.0,
    "profit_factor_scale": 2.5,
    "drawdown_weight": 15.0,
    "drawdown_scale": 15.0,
    "trades_weight": 5.0,
    "trade_count_weight": 5.0,
    "trade_count_scale": 100.0,
    "wfo_weight": 20.0,
    "mc_weight": 10.0,
    "sharpe_weight": 0.0,
    "sharpe_scale": 2.0,
    "stagnation_weight": 10.0,
    "stagnation_scale": 300.0,
    "stability_weight": 0.0,
}

PRESETS_DIR = ROOT / "config" / "strategy_presets"

def _load_preset(filename: str, default: Any = None) -> Any:
    path = PRESETS_DIR / filename
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return default or {}
