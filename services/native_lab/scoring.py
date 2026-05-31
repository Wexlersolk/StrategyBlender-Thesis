from __future__ import annotations

from typing import Any

import pandas as pd

from services.native_lab.config import DEFAULT_SCORING_PROFILE
from services.native_lab.family_registry import FamilyRegistry


def default_scoring_profile_for_template(template_name: str) -> dict[str, Any]:
    family = FamilyRegistry.get(template_name)
    profile = dict(DEFAULT_SCORING_PROFILE)
    if family:
        profile.update(family.get_scoring_profile())
    return profile


def resolve_scoring_profile(record: dict[str, Any]) -> dict[str, Any]:
    profile = default_scoring_profile_for_template(str(record.get("template_name", "")))
    profile.update(record.get("scoring_profile", {}) or {})
    return profile


def mt5_correlation_score(comparison: dict[str, Any] | None) -> float:
    if not isinstance(comparison, dict) or not comparison:
        return 0.0
    profit_ratio = min(1.0, max(0.0, float(comparison.get("profit_ratio_mt5_to_native", 0.0) or 0.0) / 0.8))
    pf_ratio = min(1.0, max(0.0, float(comparison.get("profit_factor_ratio_mt5_to_native", 0.0) or 0.0) / 0.85))
    trade_ratio_raw = float(comparison.get("trade_count_ratio_mt5_to_native", 0.0) or 0.0)
    if trade_ratio_raw >= 1.0:
        trade_distance = max(0.0, trade_ratio_raw - 1.0)
        trade_ratio = max(0.0, 1.0 - (trade_distance / 0.22))
    else:
        trade_distance = max(0.0, 1.0 - trade_ratio_raw)
        trade_ratio = max(0.0, 1.0 - (trade_distance / 0.32))
    dd_ratio_raw = float(comparison.get("drawdown_ratio_mt5_to_native", 99.0) or 99.0)
    dd_ratio = max(0.0, 1.0 - max(0.0, dd_ratio_raw - 1.0) / 1.1)
    return round((profit_ratio * 0.30) + (pf_ratio * 0.30) + (trade_ratio * 0.25) + (dd_ratio * 0.15), 4)


def suspicious_score(symbol: str, backtest: dict[str, Any], mt5_comparison: dict[str, Any] | None = None) -> float:
    normalized = str(symbol or "").strip().upper()
    pf = float(backtest.get("profit_factor", 0.0) or 0.0)
    dd = float(backtest.get("max_drawdown_pct", 0.0) or 0.0)
    trades = float(backtest.get("num_trades", 0.0) or 0.0)
    sharpe = float(backtest.get("sharpe_mean", 0.0) or 0.0)
    win_rate = float(backtest.get("win_rate", 0.0) or 0.0)
    score = 0.0

    if normalized in {"HK50.CASH", "US100.CASH", "US30.CASH", "UK100.CASH", "GER40.CASH", "GER40"}:
        if pf > 4.0:
            score += min(0.45, (pf - 4.0) / 12.0)
        if dd < 1.5 and trades >= 40:
            score += min(0.30, (1.5 - dd) / 1.5 * 0.30)
        if sharpe > 3.0:
            score += min(0.20, (sharpe - 3.0) / 4.0 * 0.20)
    if normalized == "US100.CASH":
        if trades >= 2200 and win_rate < 0.43:
            score += min(0.22, (0.43 - win_rate) / 0.10 * 0.22)
        if pf > 1.8 and win_rate < 0.45:
            score += min(0.18, (0.45 - win_rate) / 0.08 * 0.18)
    if normalized == "HK50.CASH":
        if pf > 2.5:
            score += min(0.55, (pf - 2.5) / 6.0)
        if dd < 4.0 and trades >= 120:
            score += min(0.35, (4.0 - dd) / 4.0 * 0.35)
        if sharpe > 2.0:
            score += min(0.20, (sharpe - 2.0) / 2.5 * 0.20)
        if trades > 260:
            score += min(0.15, (trades - 260.0) / 180.0 * 0.15)
    if normalized == "XAUUSD" and pf > 3.5 and dd < 2.0 and trades >= 80:
        score += 0.15

    if isinstance(mt5_comparison, dict) and mt5_comparison:
        trade_ratio = float(mt5_comparison.get("trade_count_ratio_mt5_to_native", 1.0) or 0.0)
        dd_ratio = float(mt5_comparison.get("drawdown_ratio_mt5_to_native", 1.0) or 0.0)
        pf_ratio = float(mt5_comparison.get("profit_factor_ratio_mt5_to_native", 1.0) or 0.0)
        if trade_ratio < 0.65:
            score += min(0.22, (0.65 - trade_ratio) * 0.45)
        if trade_ratio > 1.25:
            score += min(0.42, (trade_ratio - 1.25) * 0.28)
        if pf_ratio < 0.7:
            score += min(0.20, (0.7 - pf_ratio) * 0.5)
        if dd_ratio > 1.8:
            score += min(0.22, (dd_ratio - 1.8) * 0.12)

    return round(min(1.0, max(0.0, score)), 4)


def score_candidate(
    *,
    template_name: str,
    backtest: dict[str, Any],
    wfo: dict[str, Any],
    monte_carlo: dict[str, Any],
    stability_score: float,
    scoring_profile: dict[str, Any] | None = None,
) -> tuple[float, dict[str, float], dict[str, Any]]:
    profile = dict(scoring_profile or default_scoring_profile_for_template(template_name))
    
    def _get(key: str, default: float = 0.0) -> float:
        return float(profile.get(key, default))

    num_trades = int(backtest.get("num_trades", 0) or 0)
    
    # Penalize low-trade strategies to avoid ranking "dead" or lucky single-trade strategies
    if num_trades < 5:
        sharpe_component = 0.0
        profit_factor_component = 0.0
        drawdown_component = 0.0
        trade_count_component = 0.0
        win_rate_component = 0.0
        stagnation_component = 0.0
    else:
        pf = float(backtest.get("profit_factor", 0.0) or 0.0)
        pf_scale = max(1e-9, _get("profit_factor_scale", 2.0))
        pf_weight = _get("profit_factor_weight", 40.0)
        
        # Harsh penalty for PF < 1.0 (losing money)
        if pf < 1.0:
            profit_factor_component = (pf - 1.0) * pf_weight * 2.0 # Negative score for losers
        elif pf < 1.1:
            profit_factor_component = (pf / pf_scale) * pf_weight * 0.5 # Half weight for marginal
        else:
            profit_factor_component = min(1.0, pf / pf_scale) * pf_weight
            
        sharpe = float(backtest.get("sharpe_mean", 0.0) or 0.0)
        if sharpe < 0 and pf < 1.0:
            sharpe_component = sharpe * _get("sharpe_weight", 0.0) # Negative sharpe penalizes
        else:
            sharpe_component = min(1.0, max(0.0, sharpe / max(1e-9, _get("sharpe_scale", 2.0)))) * _get("sharpe_weight", 0.0)
            
        drawdown_component = max(0.0, 1.0 - min(1.0, backtest.get("max_drawdown_pct", 100.0) / max(1e-9, _get("drawdown_scale", 15.0)))) * _get("drawdown_weight", 20.0)
        
        # Trade count should not reward overtrading if losing
        trade_count_raw = min(1.0, backtest.get("num_trades", 0) / max(1e-9, _get("trade_count_scale", 50.0)))
        if pf < 1.0:
            trade_count_component = trade_count_raw * _get("trade_count_weight", 10.0) * -1.0 # Penalize overtrading if losing
        else:
            trade_count_component = trade_count_raw * _get("trade_count_weight", 10.0)
        
        win_rate = float(backtest.get("win_rate", 0.0) or 0.0)
        win_rate_floor = _get("win_rate_floor", 0.35)
        win_rate_target = max(win_rate_floor + 1e-9, _get("win_rate_target", 0.55))
        if win_rate <= win_rate_floor:
            win_rate_ratio = 0.0
        elif win_rate >= win_rate_target:
            win_rate_ratio = 1.0
        else:
            win_rate_ratio = (win_rate - win_rate_floor) / (win_rate_target - win_rate_floor)
        win_rate_component = max(0.0, min(1.0, win_rate_ratio)) * _get("win_rate_weight", 0.0)
        
        max_recovery_days = float(backtest.get("max_recovery_days", 0.0) or 0.0)
        stagnation_component = max(0.0, 1.0 - (max_recovery_days / max(1e-9, _get("stagnation_scale", 300.0)))) * _get("stagnation_weight", 0.0)
    
    wfo_component = float(wfo.get("robustness_score", 0.0)) * _get("wfo_weight", 20.0) if isinstance(wfo, dict) else 0.0
    mc_component = float(monte_carlo.get("prob_profit", 0.0)) * _get("mc_weight", 10.0) if isinstance(monte_carlo, dict) else 0.0
    stability_component = float(stability_score) * _get("stability_weight", 0.0)
    equity_stability_component = float(backtest.get("equity_stability", 0.0)) * _get("equity_stability_weight", 0.0)

    components = {
        "sharpe": round(sharpe_component, 4),
        "profit_factor": round(profit_factor_component, 4),
        "drawdown": round(drawdown_component, 4),
        "trade_count": round(trade_count_component, 4),
        "win_rate": round(win_rate_component, 4),
        "stagnation": round(stagnation_component, 4),
        "wfo": round(wfo_component, 4),
        "monte_carlo": round(mc_component, 4),
        "stability": round(stability_component, 4),
        "equity_stability": round(equity_stability_component, 4),
    }
    score = round(sum(components.values()), 2)
    return score, components, profile


def param_stability_score(params_used: list[dict[str, Any]]) -> float:
    if len(params_used) <= 1:
        return 1.0
    numeric_keys = sorted({key for params in params_used for key, value in params.items() if isinstance(value, (int, float))})
    if not numeric_keys:
        return 1.0
    penalties: list[float] = []
    for key in numeric_keys:
        values = [float(params[key]) for params in params_used if key in params]
        if len(values) <= 1:
            continue
        mean = sum(values) / len(values)
        if abs(mean) < 1e-9:
            penalties.append(0.0)
            continue
        std = pd.Series(values).std(ddof=0)
        penalties.append(min(1.0, float(std / abs(mean))))
    if not penalties:
        return 1.0
    return max(0.0, 1.0 - float(sum(penalties) / len(penalties)))
