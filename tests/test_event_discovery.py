from __future__ import annotations

import numpy as np
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.event_discovery import (
    build_xauusd_event_hypotheses,
    discover_event_hypotheses,
    hypothesis_signal_mask,
    prepare_event_features,
)


def _synthetic_xau_frame(periods: int = 600) -> pd.DataFrame:
    index = pd.date_range("2022-01-03", periods=periods, freq="1h")
    close: list[float] = []
    price = 1800.0
    for i in range(periods):
        if i % 30 in {10, 11, 12}:
            price += 7.5
        elif i % 30 == 13:
            price += 10.0
        elif i % 45 == 20:
            price -= 14.0
        elif i % 45 == 21:
            price += 9.0
        else:
            price += 0.25 + 0.15 * np.sin(i / 11.0)
        close.append(price)
    close_series = pd.Series(close, index=index)
    open_series = close_series.shift(1).fillna(close_series.iloc[0] - 0.5)
    high_series = pd.concat([open_series, close_series], axis=1).max(axis=1) + 1.6
    low_series = pd.concat([open_series, close_series], axis=1).min(axis=1) - 1.6
    volume = pd.Series(100 + (np.arange(periods) % 10), index=index)
    return pd.DataFrame(
        {
            "open": open_series,
            "high": high_series,
            "low": low_series,
            "close": close_series,
            "volume": volume,
        },
        index=index,
    )


def test_xau_event_library_exposes_multiple_families():
    hypotheses = build_xauusd_event_hypotheses()

    assert hypotheses
    families = {item.family for item in hypotheses}
    assert "compression_breakout" in families
    assert "sweep_reclaim" in families
    assert "impulse_pullback" in families


def test_hypothesis_signal_mask_produces_events_on_synthetic_series():
    df = prepare_event_features(_synthetic_xau_frame())
    hypothesis = next(
        item
        for item in build_xauusd_event_hypotheses()
        if item.family == "compression_breakout"
        and item.side == "long"
        and item.regime == "any"
        and item.session == "london_ny"
        and item.lookback == 12
        and item.hold_bars == 4
        and item.params["compression_cap"] == 0.85
        and item.params["expansion_floor"] == 1.2
    )

    mask = hypothesis_signal_mask(df, hypothesis)

    assert mask.any()


def test_discover_event_hypotheses_returns_ranked_diverse_results():
    df = _synthetic_xau_frame()
    hypotheses = build_xauusd_event_hypotheses()

    results = discover_event_hypotheses(df, hypotheses, top_n=5, min_signals=2)

    assert results
    assert len(results) <= 5
    assert all(item.signal_count >= 2 for item in results)
    assert all(0.0 <= item.novelty_score <= 1.0 for item in results)
    assert results[0].total_score >= results[-1].total_score
