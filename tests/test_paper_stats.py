from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.paper_stats import aligned_window_deltas, compare_overlays_to_baseline


def _split_metrics() -> pd.DataFrame:
    rows = []
    baseline = [10.0, -5.0, 8.0, -3.0, 11.0]
    benchmark = [11.0, -4.0, 8.5, -1.0, 12.0]
    ml_overlay = [14.0, -1.0, 10.0, 1.0, 15.0]
    for window_id, (base, bench, ml) in enumerate(zip(baseline, benchmark, ml_overlay, strict=False)):
        rows.extend(
            [
                {"asset_id": "asset_a", "overlay": "Baseline", "window_id": window_id, "oos_net_profit": base},
                {"asset_id": "asset_a", "overlay": "Benchmark", "window_id": window_id, "oos_net_profit": bench},
                {"asset_id": "asset_a", "overlay": "ML Overlay", "window_id": window_id, "oos_net_profit": ml},
            ]
        )
    return pd.DataFrame(rows)


def test_aligned_window_deltas_returns_overlay_minus_baseline():
    deltas = aligned_window_deltas(_split_metrics())

    assert not deltas.empty
    assert set(deltas["overlay"]) == {"Benchmark", "ML Overlay"}
    assert (deltas[deltas["overlay"] == "ML Overlay"]["delta"] > 0).all()


def test_compare_overlays_to_baseline_reports_positive_ml_improvement():
    summary, deltas = compare_overlays_to_baseline(_split_metrics(), bootstrap_samples=500, permutation_samples=500, seed=7)

    assert not deltas.empty
    assert not summary.empty
    ml_row = summary.loc[summary["overlay"] == "ML Overlay"].iloc[0]
    assert ml_row["mean_delta_profit"] > 0
    assert ml_row["bootstrap_ci_high"] >= ml_row["bootstrap_ci_low"]
