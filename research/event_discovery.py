from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import product
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EventHypothesis:
    hypothesis_id: str
    label: str
    symbol: str
    timeframe: str
    family: str
    side: str
    regime: str
    session: str
    lookback: int
    hold_bars: int
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventDiscoveryResult:
    hypothesis: EventHypothesis
    signal_count: int
    coverage_pct: float
    avg_return: float
    median_return: float
    win_rate: float
    payoff_ratio: float
    return_std: float
    sharpe_like: float
    yearly_consistency: float
    split_consistency: float
    regime_balance: float
    fitness_score: float
    novelty_score: float
    total_score: float
    signal_times: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["hypothesis"] = asdict(self.hypothesis)
        return payload


def prepare_event_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out.columns = [str(col).lower() for col in out.columns]
    for column in ["open", "high", "low", "close"]:
        if column not in out.columns:
            raise ValueError(f"Missing required OHLC column: {column}")

    bar_range = (out["high"] - out["low"]).clip(lower=1e-9)
    true_range = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["close"].shift(1)).abs(),
            (out["low"] - out["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["bar_range"] = bar_range
    out["body"] = out["close"] - out["open"]
    out["body_pct"] = out["body"] / bar_range
    out["close_location"] = (out["close"] - out["low"]) / bar_range
    out["atr_fast"] = true_range.rolling(14, min_periods=14).mean()
    out["atr_slow"] = true_range.rolling(48, min_periods=48).mean()
    out["range_ratio"] = bar_range / out["atr_fast"].replace(0.0, np.nan)
    out["compression_ratio"] = out["atr_fast"] / out["atr_slow"].replace(0.0, np.nan)
    out["ret_6"] = out["close"].pct_change(6)
    out["ret_24"] = out["close"].pct_change(24)
    out["drift_strength"] = (out["close"] - out["close"].shift(24)) / out["atr_slow"].replace(0.0, np.nan)
    out["hour"] = out.index.hour
    out["weekday"] = out.index.weekday
    out["year"] = out.index.year
    return out.replace([np.inf, -np.inf], np.nan)


def build_xauusd_event_hypotheses(*, timeframe: str = "H1") -> list[EventHypothesis]:
    symbol = "XAUUSD"
    hypotheses: list[EventHypothesis] = []
    counter = 0

    def _append(
        *,
        family: str,
        side: str,
        regime: str,
        session: str,
        lookback: int,
        hold_bars: int,
        params: dict[str, Any],
    ) -> None:
        nonlocal counter
        counter += 1
        hypotheses.append(
            EventHypothesis(
                hypothesis_id=f"xau_event_{counter:04d}",
                label=f"{family}:{side}:{regime}:{session}:{lookback}:{hold_bars}",
                symbol=symbol,
                timeframe=timeframe,
                family=family,
                side=side,
                regime=regime,
                session=session,
                lookback=lookback,
                hold_bars=hold_bars,
                params=dict(params),
            )
        )

    for lookback, hold_bars, compression_cap, expansion_floor, session, regime, side in product(
        [12, 24, 36],
        [4, 8, 12],
        [0.72, 0.85],
        [1.2, 1.5],
        ["london_ny", "london_only", "ny_only"],
        ["any", "drift_up", "drift_down"],
        ["long", "short"],
    ):
        _append(
            family="compression_breakout",
            side=side,
            regime=regime,
            session=session,
            lookback=lookback,
            hold_bars=hold_bars,
            params={
                "compression_cap": compression_cap,
                "expansion_floor": expansion_floor,
            },
        )

    for lookback, hold_bars, reclaim_location, session, regime, side in product(
        [12, 24, 36],
        [2, 4, 8],
        [0.55, 0.65],
        ["all_day", "london_ny", "ny_only"],
        ["any", "balance", "drift_up", "drift_down"],
        ["long", "short"],
    ):
        _append(
            family="sweep_reclaim",
            side=side,
            regime=regime,
            session=session,
            lookback=lookback,
            hold_bars=hold_bars,
            params={"reclaim_location": reclaim_location},
        )

    for hold_bars, pullback_cap, impulse_floor, session, side in product(
        [4, 8, 12],
        [0.45, 0.65],
        [1.0, 1.4],
        ["london_ny", "all_day"],
        ["long", "short"],
    ):
        _append(
            family="impulse_pullback",
            side=side,
            regime="drift_up" if side == "long" else "drift_down",
            session=session,
            lookback=24,
            hold_bars=hold_bars,
            params={
                "pullback_cap": pullback_cap,
                "impulse_floor": impulse_floor,
            },
        )

    return hypotheses


def discover_event_hypotheses(
    df: pd.DataFrame,
    hypotheses: list[EventHypothesis],
    *,
    top_n: int = 20,
    min_signals: int = 25,
) -> list[EventDiscoveryResult]:
    features = prepare_event_features(df)
    scored: list[tuple[EventDiscoveryResult, np.ndarray]] = []
    for hypothesis in hypotheses:
        mask = hypothesis_signal_mask(features, hypothesis)
        result = score_event_hypothesis(features, hypothesis, mask=mask, min_signals=min_signals)
        if result is None:
            continue
        scored.append((result, mask.to_numpy(dtype=bool)))

    scored.sort(key=lambda item: item[0].fitness_score, reverse=True)

    selected: list[tuple[EventDiscoveryResult, np.ndarray]] = []
    for result, mask in scored:
        novelty = _novelty_score(mask, [existing_mask for _, existing_mask in selected])
        result.novelty_score = round(novelty, 4)
        result.total_score = round(0.8 * float(result.fitness_score) + 0.2 * novelty, 4)
        selected.append((result, mask))

    selected.sort(key=lambda item: item[0].total_score, reverse=True)

    diversified: list[tuple[EventDiscoveryResult, np.ndarray]] = []
    for result, mask in selected:
        novelty = _novelty_score(mask, [existing_mask for _, existing_mask in diversified])
        result.novelty_score = round(novelty, 4)
        result.total_score = round(0.75 * float(result.fitness_score) + 0.25 * novelty, 4)
        if diversified and novelty < 0.20:
            continue
        diversified.append((result, mask))
        if len(diversified) >= int(top_n):
            break
    return [result for result, _ in diversified]


def score_event_hypothesis(
    df: pd.DataFrame,
    hypothesis: EventHypothesis,
    *,
    mask: pd.Series | None = None,
    min_signals: int = 25,
) -> EventDiscoveryResult | None:
    if mask is None:
        mask = hypothesis_signal_mask(df, hypothesis)
    side_sign = 1.0 if hypothesis.side == "long" else -1.0
    entry = df["open"].shift(-1)
    exit_ = df["close"].shift(-int(hypothesis.hold_bars))
    event_returns = side_sign * ((exit_ / entry) - 1.0)
    valid_mask = mask & entry.notna() & exit_.notna()
    if int(valid_mask.sum()) < int(min_signals):
        return None

    sample = event_returns.loc[valid_mask].dropna()
    if len(sample) < int(min_signals):
        return None

    wins = sample[sample > 0.0]
    losses = sample[sample <= 0.0]
    avg_return = float(sample.mean())
    median_return = float(sample.median())
    return_std = float(sample.std(ddof=0))
    sharpe_like = avg_return / max(return_std, 1e-9)
    win_rate = float((sample > 0.0).mean())
    avg_win = float(wins.mean()) if not wins.empty else 0.0
    avg_loss = abs(float(losses.mean())) if not losses.empty else 0.0
    payoff_ratio = avg_win / max(avg_loss, 1e-9) if avg_win > 0.0 else 0.0

    signal_years = df.loc[valid_mask, "year"]
    yearly_means = sample.groupby(signal_years).mean()
    yearly_consistency = float((yearly_means > 0.0).mean()) if len(yearly_means) else 0.0

    thirds = np.array_split(sample.to_numpy(), 3)
    split_consistency = float(np.mean([float(np.mean(split) > 0.0) for split in thirds if len(split)])) if len(sample) else 0.0

    if hypothesis.regime == "any":
        regime_balance = 1.0
    else:
        opposing = _opposing_regime(hypothesis.regime)
        same_mask = _regime_mask(df, hypothesis.regime)
        other_mask = _regime_mask(df, opposing) if opposing else pd.Series(False, index=df.index)
        same_count = int((valid_mask & same_mask).sum())
        other_count = int((valid_mask & other_mask).sum())
        regime_balance = same_count / max(same_count + other_count, 1)

    sample_quality = min(1.0, len(sample) / 120.0)
    edge_component = _bounded_score(avg_return * 10_000.0, 0.0, 12.0)
    sharpe_component = _bounded_score(sharpe_like, 0.0, 0.35)
    win_component = _bounded_score(win_rate, 0.48, 0.62)
    payoff_component = _bounded_score(payoff_ratio, 0.9, 1.8)
    stability_component = 0.5 * yearly_consistency + 0.5 * split_consistency
    fitness = (
        0.22 * edge_component
        + 0.22 * sharpe_component
        + 0.16 * win_component
        + 0.14 * payoff_component
        + 0.18 * stability_component
        + 0.08 * sample_quality
    )

    return EventDiscoveryResult(
        hypothesis=hypothesis,
        signal_count=int(len(sample)),
        coverage_pct=round(100.0 * len(sample) / max(len(df), 1), 4),
        avg_return=round(avg_return, 6),
        median_return=round(median_return, 6),
        win_rate=round(win_rate, 4),
        payoff_ratio=round(payoff_ratio, 4),
        return_std=round(return_std, 6),
        sharpe_like=round(sharpe_like, 4),
        yearly_consistency=round(yearly_consistency, 4),
        split_consistency=round(split_consistency, 4),
        regime_balance=round(regime_balance, 4),
        fitness_score=round(fitness, 4),
        novelty_score=0.0,
        total_score=round(fitness, 4),
        signal_times=[ts.isoformat() for ts in sample.index[:25]],
    )


def hypothesis_signal_mask(df: pd.DataFrame, hypothesis: EventHypothesis) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    family = hypothesis.family
    regime_mask = _regime_mask(df, hypothesis.regime)
    session_mask = _session_mask(df, hypothesis.session)
    lookback = int(hypothesis.lookback)
    side = hypothesis.side

    highest = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
    lowest = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)

    if family == "compression_breakout":
        compression_cap = float(hypothesis.params["compression_cap"])
        expansion_floor = float(hypothesis.params["expansion_floor"])
        base = (
            df["compression_ratio"].le(compression_cap)
            & df["range_ratio"].ge(expansion_floor)
            & session_mask
            & regime_mask
        )
        if side == "long":
            return base & df["close"].gt(highest)
        return base & df["close"].lt(lowest)

    if family == "sweep_reclaim":
        reclaim_location = float(hypothesis.params["reclaim_location"])
        base = session_mask & regime_mask & df["range_ratio"].ge(0.8)
        if side == "long":
            return (
                base
                & df["low"].lt(lowest)
                & df["close"].gt(lowest)
                & df["close_location"].ge(reclaim_location)
                & df["body_pct"].gt(0.0)
            )
        return (
            base
            & df["high"].gt(highest)
            & df["close"].lt(highest)
            & df["close_location"].le(1.0 - reclaim_location)
            & df["body_pct"].lt(0.0)
        )

    if family == "impulse_pullback":
        pullback_cap = float(hypothesis.params["pullback_cap"])
        impulse_floor = float(hypothesis.params["impulse_floor"])
        pullback_depth = (df["close"] - df["low"]) / df["atr_fast"].replace(0.0, np.nan)
        if side == "long":
            return (
                session_mask
                & regime_mask
                & df["range_ratio"].ge(impulse_floor)
                & df["body_pct"].gt(0.25)
                & df["ret_6"].lt(0.0)
                & pullback_depth.le(pullback_cap)
                & df["close"].gt(df["high"].shift(1))
            )
        pullback_depth = (df["high"] - df["close"]) / df["atr_fast"].replace(0.0, np.nan)
        return (
            session_mask
            & regime_mask
            & df["range_ratio"].ge(impulse_floor)
            & df["body_pct"].lt(-0.25)
            & df["ret_6"].gt(0.0)
            & pullback_depth.le(pullback_cap)
            & df["close"].lt(df["low"].shift(1))
        )

    raise ValueError(f"Unsupported family: {family}")


def _session_mask(df: pd.DataFrame, session: str) -> pd.Series:
    hour = df["hour"]
    if session == "all_day":
        return pd.Series(True, index=df.index)
    if session == "london_only":
        return hour.between(6, 11)
    if session == "ny_only":
        return hour.between(12, 17)
    if session == "london_ny":
        return hour.between(6, 17)
    raise ValueError(f"Unsupported session: {session}")


def _regime_mask(df: pd.DataFrame, regime: str) -> pd.Series:
    if regime == "any":
        return pd.Series(True, index=df.index)
    if regime == "drift_up":
        return df["drift_strength"].ge(1.0) & df["ret_24"].gt(0.0)
    if regime == "drift_down":
        return df["drift_strength"].le(-1.0) & df["ret_24"].lt(0.0)
    if regime == "balance":
        return df["drift_strength"].abs().le(0.75) & df["compression_ratio"].le(1.05)
    raise ValueError(f"Unsupported regime: {regime}")


def _opposing_regime(regime: str) -> str | None:
    if regime == "drift_up":
        return "drift_down"
    if regime == "drift_down":
        return "drift_up"
    return None


def _bounded_score(value: float, floor: float, cap: float) -> float:
    if cap <= floor:
        return 0.0
    normalized = (float(value) - float(floor)) / (float(cap) - float(floor))
    return max(0.0, min(1.0, normalized))


def _novelty_score(mask: np.ndarray, previous_masks: list[np.ndarray]) -> float:
    if not previous_masks:
        return 1.0
    current = mask.astype(bool)
    if not current.any():
        return 0.0
    best_similarity = 0.0
    for other in previous_masks:
        union = np.logical_or(current, other).sum()
        if union <= 0:
            continue
        similarity = float(np.logical_and(current, other).sum()) / float(union)
        best_similarity = max(best_similarity, similarity)
    return max(0.0, 1.0 - best_similarity)
