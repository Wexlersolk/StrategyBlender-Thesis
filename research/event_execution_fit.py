from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from engine.backtester import Backtester
from engine.base_strategy import BaseStrategy, BarContext
from research.event_discovery import EventHypothesis, hypothesis_signal_mask, prepare_event_features
from services.backtest_service import resolve_execution_config


@dataclass(frozen=True)
class ExecutionPolicy:
    policy_id: str
    entry_style: str
    stop_model: str
    target_model: str
    timeout_bars: int
    trail_style: str
    entry_buffer_atr: float
    stop_atr: float
    target_r: float
    target_atr: float
    trail_atr: float
    trail_activation_r: float
    order_expiry_bars: int = 2


@dataclass
class EventPolicyFit:
    hypothesis: EventHypothesis
    policy: ExecutionPolicy
    train_summary: dict[str, Any]
    test_summary: dict[str, Any]
    fit_score: float
    robustness_score: float
    total_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis": asdict(self.hypothesis),
            "policy": asdict(self.policy),
            "train_summary": dict(self.train_summary),
            "test_summary": dict(self.test_summary),
            "fit_score": self.fit_score,
            "robustness_score": self.robustness_score,
            "total_score": self.total_score,
        }


def event_hypothesis_from_dict(payload: dict[str, Any]) -> EventHypothesis:
    return EventHypothesis(**payload)


def build_execution_policy_grid() -> list[ExecutionPolicy]:
    policies: list[ExecutionPolicy] = []
    counter = 0
    for entry_style in ["market", "breakout_stop"]:
        for stop_model in ["atr", "signal_range"]:
            for target_model in ["rr", "atr"]:
                for timeout_bars in [4, 8, 12]:
                    for trail_style in ["none", "atr"]:
                        for stop_atr in [1.2, 1.8, 2.4]:
                            for target_value in [1.5, 2.5, 3.5]:
                                for entry_buffer_atr in ([0.0] if entry_style == "market" else [0.05, 0.15]):
                                    if trail_style == "none":
                                        trail_atr = 0.0
                                        trail_activation_r = 0.0
                                        trail_options = [(trail_atr, trail_activation_r)]
                                    else:
                                        trail_options = [(1.0, 0.75), (1.5, 1.0), (2.0, 1.25)]
                                    for trail_atr, trail_activation_r in trail_options:
                                        counter += 1
                                        policies.append(
                                            ExecutionPolicy(
                                                policy_id=f"policy_{counter:04d}",
                                                entry_style=entry_style,
                                                stop_model=stop_model,
                                                target_model=target_model,
                                                timeout_bars=timeout_bars,
                                                trail_style=trail_style,
                                                entry_buffer_atr=entry_buffer_atr,
                                                stop_atr=stop_atr,
                                                target_r=target_value,
                                                target_atr=target_value,
                                                trail_atr=trail_atr,
                                                trail_activation_r=trail_activation_r,
                                                order_expiry_bars=2 if entry_style == "breakout_stop" else 1,
                                            )
                                        )
    return policies


def build_event_strategy_class(hypothesis: EventHypothesis, policy: ExecutionPolicy):
    class EventExecutionStrategy(BaseStrategy):
        name = f"{hypothesis.label}|{policy.policy_id}"
        symbol = hypothesis.symbol
        timeframe = hypothesis.timeframe
        params: dict[str, Any] = {}
        lot_value = 100.0 if str(hypothesis.symbol).upper() == "XAUUSD" else 1.0

        def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
            out = prepare_event_features(df)
            out["event_signal"] = hypothesis_signal_mask(out, hypothesis).astype(int)
            return out

        def on_bar(self, ctx: BarContext):
            i = ctx.bar_index
            if i < max(2, int(hypothesis.lookback) + 1):
                return
            if ctx.has_position or ctx.has_pending:
                return
            if not bool(ctx._df["event_signal"].iloc[i - 1]):
                return

            atr = float(ctx._df["atr_fast"].iloc[i - 1])
            if not pd.notna(atr) or atr <= 0.0:
                return

            signal_high = float(ctx._df["high"].iloc[i - 1])
            signal_low = float(ctx._df["low"].iloc[i - 1])
            signal_close = float(ctx._df["close"].iloc[i - 1])
            signal_range = max(signal_high - signal_low, atr * 0.5)

            if hypothesis.side == "long":
                entry_price = ctx.open if policy.entry_style == "market" else signal_high + (policy.entry_buffer_atr * atr)
                stop_dist = policy.stop_atr * atr if policy.stop_model == "atr" else max(signal_range, 0.8 * atr)
                stop_loss = entry_price - stop_dist
                target_dist = stop_dist * policy.target_r if policy.target_model == "rr" else policy.target_atr * atr
                take_profit = entry_price + target_dist
            else:
                entry_price = ctx.open if policy.entry_style == "market" else signal_low - (policy.entry_buffer_atr * atr)
                stop_dist = policy.stop_atr * atr if policy.stop_model == "atr" else max(signal_range, 0.8 * atr)
                stop_loss = entry_price + stop_dist
                target_dist = stop_dist * policy.target_r if policy.target_model == "rr" else policy.target_atr * atr
                take_profit = entry_price - target_dist

            self._next_exit_after_bars = int(policy.timeout_bars)
            if policy.trail_style == "atr":
                self._next_trail_dist = float(policy.trail_atr * atr)
                self._next_trail_activation = float(policy.trail_activation_r * stop_dist)
            else:
                self._next_trail_dist = 0.0
                self._next_trail_activation = 0.0

            if hypothesis.side == "long":
                if policy.entry_style == "market":
                    ctx.buy_market(sl=stop_loss, tp=take_profit, lots=1.0, comment=policy.policy_id)
                else:
                    ctx.buy_stop(
                        price=entry_price,
                        sl=stop_loss,
                        tp=take_profit,
                        lots=1.0,
                        expiry_bars=int(policy.order_expiry_bars),
                        comment=policy.policy_id,
                    )
            else:
                if policy.entry_style == "market":
                    ctx.sell_market(sl=stop_loss, tp=take_profit, lots=1.0, comment=policy.policy_id)
                else:
                    ctx.sell_stop(
                        price=entry_price,
                        sl=stop_loss,
                        tp=take_profit,
                        lots=1.0,
                        expiry_bars=int(policy.order_expiry_bars),
                        comment=policy.policy_id,
                    )

    return EventExecutionStrategy


def fit_execution_policies(
    df: pd.DataFrame,
    hypothesis: EventHypothesis,
    *,
    policies: list[ExecutionPolicy] | None = None,
    top_n: int = 10,
    train_fraction: float = 0.7,
) -> list[EventPolicyFit]:
    if df.empty:
        return []
    policies = policies or build_execution_policy_grid()
    split_idx = max(100, min(len(df) - 100, int(len(df) * float(train_fraction))))
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    execution = resolve_execution_config(hypothesis.symbol)

    evaluated: list[EventPolicyFit] = []
    for policy in policies:
        strategy_class = build_event_strategy_class(hypothesis, policy)
        train_results = _run_event_backtest(strategy_class, train_df, execution)
        test_results = _run_event_backtest(strategy_class, test_df, execution)
        train_summary = train_results.summary()
        test_summary = test_results.summary()
        fit_score = _policy_score(test_summary)
        robustness = _policy_robustness(train_summary, test_summary)
        total = round(0.7 * fit_score + 0.3 * robustness, 4)
        evaluated.append(
            EventPolicyFit(
                hypothesis=hypothesis,
                policy=policy,
                train_summary=train_summary,
                test_summary=test_summary,
                fit_score=round(fit_score, 4),
                robustness_score=round(robustness, 4),
                total_score=total,
            )
        )

    evaluated.sort(key=lambda item: item.total_score, reverse=True)
    return evaluated[: max(1, int(top_n))]


def load_discovery_results(path: str | Path) -> list[EventHypothesis]:
    payload = json_load(Path(path))
    results = payload.get("results", []) if isinstance(payload, dict) else []
    hypotheses: list[EventHypothesis] = []
    for item in results:
        hypothesis_payload = item.get("hypothesis", {}) if isinstance(item, dict) else {}
        if hypothesis_payload:
            hypotheses.append(event_hypothesis_from_dict(hypothesis_payload))
    return hypotheses


def json_load(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def latest_xau_discovery_file(root: Path) -> Path | None:
    files = sorted(root.glob("xau_event_discovery_*.json"))
    return files[-1] if files else None


def _run_event_backtest(strategy_class, df: pd.DataFrame, execution: dict[str, Any]):
    bt = Backtester(
        initial_capital=100_000,
        lot_value=getattr(strategy_class, "lot_value", 1.0),
        intrabar_steps=60 if str(getattr(strategy_class, "symbol", "")).upper() == "XAUUSD" and str(getattr(strategy_class, "timeframe", "")).upper() == "H1" else 1,
        commission_per_lot=float(execution["commission_per_lot"]),
        spread_pips=float(execution["spread_pips"]),
        slippage_pips=float(execution["slippage_pips"]),
        tick_size=float(execution["tick_size"]),
        tick_value=float(execution["tick_value"]),
        contract_size=float(execution["contract_size"]),
        swap_per_lot_long=float(execution["swap_per_lot_long"]),
        swap_per_lot_short=float(execution["swap_per_lot_short"]),
        swap_weekday_multipliers=dict(execution.get("swap_weekday_multipliers", {})),
        session_timezone_offset_hours=float(execution["session_timezone_offset_hours"]),
        use_bar_spread=bool(execution["use_bar_spread"]),
    )
    return bt.run(strategy_class(), df.copy())


def _policy_score(summary: dict[str, Any]) -> float:
    pf = float(summary.get("profit_factor", 0.0) or 0.0)
    sharpe = float(summary.get("sharpe_ratio", 0.0) or 0.0)
    dd = float(summary.get("max_drawdown_pct", 100.0) or 100.0)
    trades = int(summary.get("n_trades", 0) or 0)
    net_profit = float(summary.get("net_profit", 0.0) or 0.0)
    pf_score = _bounded(pf, 1.0, 2.2)
    sharpe_score = _bounded(sharpe, 0.0, 2.5)
    dd_score = 1.0 - _bounded(dd, 5.0, 30.0)
    trade_score = _bounded(trades, 15.0, 120.0)
    profit_score = _bounded(net_profit, 0.0, 60_000.0)
    return max(0.0, 0.28 * pf_score + 0.24 * sharpe_score + 0.2 * dd_score + 0.14 * trade_score + 0.14 * profit_score)


def _policy_robustness(train_summary: dict[str, Any], test_summary: dict[str, Any]) -> float:
    train_pf = float(train_summary.get("profit_factor", 0.0) or 0.0)
    test_pf = float(test_summary.get("profit_factor", 0.0) or 0.0)
    train_sharpe = float(train_summary.get("sharpe_ratio", 0.0) or 0.0)
    test_sharpe = float(test_summary.get("sharpe_ratio", 0.0) or 0.0)
    train_sign = 1.0 if float(train_summary.get("net_profit", 0.0) or 0.0) > 0.0 else 0.0
    test_sign = 1.0 if float(test_summary.get("net_profit", 0.0) or 0.0) > 0.0 else 0.0
    pf_consistency = 1.0 - min(1.0, abs(test_pf - train_pf) / max(train_pf, 1e-9)) if train_pf > 0.0 else 0.0
    sharpe_consistency = 1.0 - min(1.0, abs(test_sharpe - train_sharpe) / max(abs(train_sharpe), 1e-9)) if abs(train_sharpe) > 0.0 else 0.0
    sign_consistency = 1.0 if train_sign == test_sign and test_sign == 1.0 else 0.5 if train_sign == test_sign else 0.0
    return max(0.0, 0.45 * pf_consistency + 0.35 * sharpe_consistency + 0.2 * sign_consistency)


def _bounded(value: float, floor: float, cap: float) -> float:
    if cap <= floor:
        return 0.0
    normalized = (float(value) - float(floor)) / (float(cap) - float(floor))
    return max(0.0, min(1.0, normalized))
