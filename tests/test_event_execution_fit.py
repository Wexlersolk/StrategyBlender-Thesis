from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.event_discovery import build_xauusd_event_hypotheses
from research.event_execution_fit import ExecutionPolicy, fit_execution_policies
from tests.test_event_discovery import _synthetic_xau_frame


def test_fit_execution_policies_returns_ranked_candidates():
    df = _synthetic_xau_frame(900)
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
    policies = [
        ExecutionPolicy(
            policy_id="policy_a",
            entry_style="market",
            stop_model="atr",
            target_model="rr",
            timeout_bars=4,
            trail_style="none",
            entry_buffer_atr=0.0,
            stop_atr=1.2,
            target_r=1.5,
            target_atr=1.5,
            trail_atr=0.0,
            trail_activation_r=0.0,
        ),
        ExecutionPolicy(
            policy_id="policy_b",
            entry_style="breakout_stop",
            stop_model="signal_range",
            target_model="atr",
            timeout_bars=8,
            trail_style="atr",
            entry_buffer_atr=0.05,
            stop_atr=1.8,
            target_r=2.5,
            target_atr=2.5,
            trail_atr=1.0,
            trail_activation_r=0.75,
        ),
    ]

    fits = fit_execution_policies(df, hypothesis, policies=policies, top_n=2)

    assert fits
    assert len(fits) <= 2
    assert fits[0].total_score >= fits[-1].total_score
    assert "profit_factor" in fits[0].test_summary
