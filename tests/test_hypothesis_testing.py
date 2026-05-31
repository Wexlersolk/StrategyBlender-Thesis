from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.policy import DecisionRecord
from engine.position import CloseReason, ClosedTrade, Direction
from engine.results import BacktestResults
from research.hypothesis_testing import (
    analyze_trade_hypothesis,
    directional_trade_breakdown,
    yearly_trade_breakdown,
)


def _sample_results() -> BacktestResults:
    trades: list[ClosedTrade] = []
    base_time = pd.Timestamp("2022-01-03 00:00:00")
    profits = [120, 80, -30, 95, 110, -20, 140, 60, -10, 90, 130, 70]
    for idx, profit in enumerate(profits):
        opened_time = base_time + pd.Timedelta(days=30 * idx)
        closed_time = opened_time + pd.Timedelta(hours=6)
        gross_profit = float(profit) + 2.0
        trades.append(
            ClosedTrade(
                id=idx + 1,
                direction=Direction.LONG if idx % 2 == 0 else Direction.SHORT,
                entry_price=100.0,
                exit_price=101.0,
                stop_loss=99.0,
                take_profit=103.0,
                lots=1.0,
                opened_bar=idx,
                closed_bar=idx + 1,
                opened_time=opened_time,
                closed_time=closed_time,
                close_reason=CloseReason.TAKE_PROFIT if profit > 0 else CloseReason.STOP_LOSS,
                gross_profit=gross_profit,
                commission=2.0,
                swap=0.0,
                comment="test",
            )
        )
    return BacktestResults(
        trades=trades,
        decision_records=[
            DecisionRecord(
                decision_id=idx + 1,
                time=trade.opened_time,
                bar_idx=idx,
                symbol="XAUUSD",
                timeframe="H1",
                order_type="market",
                direction=trade.direction.value,
                requested_lots=1.0,
                final_lots=1.0,
                allow_trade=True,
                policy_name="NullOverlayPolicy",
                policy_tag="pass",
                comment="",
            )
            for idx, trade in enumerate(trades)
        ],
        initial_capital=100_000.0,
        symbol="XAUUSD",
        timeframe="H1",
        date_from=base_time,
        date_to=trades[-1].closed_time,
        params={},
    )


def test_analyze_trade_hypothesis_detects_positive_expectancy():
    report = analyze_trade_hypothesis(_sample_results(), bootstrap_samples=500, permutation_samples=500, seed=7)

    assert report.sample_size == 12
    assert report.mean_profit > 0
    assert report.bootstrap_mean_ci_low < report.bootstrap_mean_ci_high
    assert report.t_pvalue_positive < 0.05
    assert report.rejects_null_positive


def test_breakdowns_return_expected_shapes():
    results = _sample_results()

    yearly = yearly_trade_breakdown(results)
    directional = directional_trade_breakdown(results)

    assert not yearly.empty
    assert list(yearly.columns) == ["year", "trades", "total_profit", "avg_profit", "median_profit", "win_rate"]
    assert set(directional["direction"]) == {"long", "short"}
