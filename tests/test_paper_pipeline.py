from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.base_strategy import BaseStrategy
from research.paper_pipeline import (
    PaperAssetConfig,
    PaperModelConfig,
    export_paper_experiment,
    run_paper_experiment,
)


class AlternatingTradeStrategy(BaseStrategy):
    params = {"lots": 1.0}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def on_bar(self, ctx):
        if ctx.has_position or ctx.has_pending:
            return
        if ctx.bar_index in {60, 62, 64, 66, 68, 70, 72, 74, 150, 152, 154, 156}:
            ctx.buy_market(sl=ctx.open - 1.0, tp=ctx.open + 1.0, lots=1.0, comment=f"bar_{ctx.bar_index}")


def _bars_with_alternating_outcomes() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=320, freq="1h")
    close = pd.Series(100.0, index=index)
    frame = pd.DataFrame(
        {
            "open": close.values,
            "high": (close + 0.25).values,
            "low": (close - 0.25).values,
            "close": close.values,
            "volume": [1.0] * len(index),
        },
        index=index,
    )
    for bar_idx in [61, 65, 69, 73, 151, 155]:
        frame.iloc[bar_idx, frame.columns.get_loc("high")] = frame.iloc[bar_idx]["open"] + 1.5
    for bar_idx in [63, 67, 71, 75, 153, 157]:
        frame.iloc[bar_idx, frame.columns.get_loc("low")] = frame.iloc[bar_idx]["open"] - 1.5
    for offset in [80, 100, 120, 180, 200, 220, 240, 260]:
        if offset + 1 < len(frame):
            frame.iloc[offset + 1, frame.columns.get_loc("high")] = frame.iloc[offset + 1]["open"] + 1.5
        if offset + 3 < len(frame):
            frame.iloc[offset + 3, frame.columns.get_loc("low")] = frame.iloc[offset + 3]["open"] - 1.5
    return frame


def test_run_paper_experiment_builds_ablation_outputs(monkeypatch, tmp_path):
    bars = _bars_with_alternating_outcomes()
    monkeypatch.setattr("research.paper_pipeline.discover_strategies", lambda: {"Alt Strategy": AlternatingTradeStrategy})
    monkeypatch.setattr("research.paper_pipeline.load_bars", lambda symbol, timeframe, date_from=None, date_to=None: bars.copy())

    report = run_paper_experiment(
        [
            PaperAssetConfig(
                asset_id="asset_a",
                strategy_ref="Alt Strategy",
                symbol="XAUUSD",
                timeframe="H1",
                date_from="2024-01-01",
                date_to="2024-02-15",
                train_bars=100,
                test_bars=80,
                embargo_bars=5,
            )
        ],
        model_config=PaperModelConfig(benchmark_name="baseline", filter_only=False),
    )

    assert not report.portfolio_report.aggregate_metrics.empty
    assert set(report.portfolio_report.aggregate_metrics["overlay"]) == {
        "Baseline",
        "Benchmark",
        "ML Filter",
        "ML Sizing",
        "ML Overlay",
    }
    assert not report.comparison_summary.empty
    assert not report.monte_carlo_summary.empty

    export_dir = export_paper_experiment(report, output_dir=tmp_path / "paper_report", title="alt_paper")
    assert (export_dir / "aggregate_metrics.csv").exists()
    assert (export_dir / "comparison_summary.tex").exists()
    assert (export_dir / "figures" / "window_profit.html").exists()
    assert (export_dir / "paper_summary.html").exists()
    assert (export_dir / "paper_report_manifest.json").exists()
