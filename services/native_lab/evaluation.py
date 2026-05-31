from __future__ import annotations

import copy
from typing import Any

from engine.data_loader import load_bars
from research.monte_carlo import run_monte_carlo
from research.walk_forward import run_wfo
from services.backtest_service import (
    backtest_result_payload,
    run_backtest,
    default_intrabar_steps,
    resolve_execution_config,
    shift_bar_times,
)
from services.native_lab.catalog import (
    get_native_strategy_record,
    upsert_native_strategy_record,
)
from services.native_lab.models import NativeStrategyRecord
from services.native_lab.mutation import (
    default_wfo_param_grid_for_template,
    default_param_grid,
    resolve_promotion_policy,
)
from services.native_lab.runtime import load_runtime_strategy_class
from services.native_lab.scoring import (
    mt5_correlation_score,
    suspicious_score,
    score_candidate,
    resolve_scoring_profile,
    param_stability_score,
)
from services.native_lab.utils import stable_hash, utc_now
from services.python_strategy_service import (
    compile_strategy_spec,
    persist_strategy_spec,
    strategy_spec_from_template,
)


def register_generated_strategy(
    *,
    template_name: str,
    payload: dict[str, Any],
    strategy_id: str,
    origin: str,
    lineage: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    promotion_policy: dict[str, Any] | None = None,
) -> tuple[dict, dict]:
    spec = strategy_spec_from_template(template_name, payload)
    compiled = compile_strategy_spec(spec, strategy_id=strategy_id)
    paths = persist_strategy_spec(compiled)

    record = NativeStrategyRecord(
        strategy_id=strategy_id,
        created_at=utc_now(),
        updated_at=utc_now(),
        name=spec.name,
        template_name=template_name,
        origin=origin,
        symbol=spec.symbol,
        timeframe=spec.timeframe,
        status="draft",
        params=spec.params,
        template_payload=copy.deepcopy(payload),
        lineage=dict(lineage or {}),
        tags=list(tags or []),
        strategy_path=paths["strategy_path"],
        spec_path=paths["spec_path"],
        strategy_module=compiled.strategy_module,
        strategy_class=compiled.strategy_class,
        promotion_policy=dict(promotion_policy or {}),
        scoring_profile=dict(payload.get("scoring_profile", {}) or {}),
    )
    
    # Optional: Log the strategy registration to a local session file if NATIVE_STRATEGY_LAB_DIR is set
    from services.native_lab.config import LAB_DIR
    session_log = LAB_DIR / "registration_log.txt"
    with open(session_log, "a", encoding="utf-8") as f:
        f.write(f"[{utc_now()}] {strategy_id} | {spec.symbol} {spec.timeframe} | {paths['strategy_path']}\n")

    return upsert_native_strategy_record(record), {
        "compiled": compiled,
        "paths": paths,
        "spec": spec,
    }


def regenerate_native_strategy_version(
    parent_strategy_id: str,
    *,
    template_name: str | None = None,
    payload: dict[str, Any] | None = None,
    origin: str = "catalog_regenerate",
) -> tuple[dict, dict]:
    parent = get_native_strategy_record(parent_strategy_id)
    if not parent:
        raise ValueError(f"Unknown native strategy: {parent_strategy_id}")
    next_template = template_name or parent["template_name"]
    next_payload = copy.deepcopy(payload or parent.get("template_payload", {}))
    child_id = f"{parent_strategy_id}_v{stable_hash({'template': next_template, 'payload': next_payload, 'ts': utc_now()})[:6]}"
    return register_generated_strategy(
        template_name=next_template,
        payload=next_payload,
        strategy_id=child_id,
        origin=origin,
        lineage={
            "parent_strategy_id": parent_strategy_id,
            "template_name": next_template,
            "version_of": parent.get("lineage", {}).get("version_of", parent_strategy_id),
        },
        tags=list(set(parent.get("tags", [])) | {"regenerated"}),
    )


def evaluate_native_strategy(
    strategy_id: str,
    *,
    date_from: str,
    date_to: str,
    intrabar_steps: int = 1,
    run_mc: bool = True,
    run_wfo_checks: bool = True,
    execution_config: dict[str, Any] | None = None,
) -> dict:
    record = get_native_strategy_record(strategy_id)
    if not record:
        raise ValueError(f"Unknown native strategy: {strategy_id}")

    strat_cls = load_runtime_strategy_class(record)
    execution_config = resolve_execution_config(record["symbol"], execution_config)
    effective_intrabar_steps = default_intrabar_steps(record["symbol"], record["timeframe"], intrabar_steps)
    result = run_backtest(
        strat_cls,
        symbol=record["symbol"],
        timeframe=record["timeframe"],
        date_from=date_from,
        date_to=date_to,
        overrides=record.get("params", {}),
        intrabar_steps=effective_intrabar_steps,
        execution_config=execution_config,
    )
    payload = backtest_result_payload(result)

    evaluation = {
        "backtest": payload["summary"],
        "score_components": {},
        "accepted": False,
        "date_from": date_from,
        "date_to": date_to,
    }

    if run_mc and result.n_trades >= 5:
        mc = run_monte_carlo(result, n_simulations=200)
        evaluation["monte_carlo"] = mc.summary()
    else:
        evaluation["monte_carlo"] = {}

    if run_wfo_checks:
        bar_time_offset_hours = float(getattr(strat_cls, "bar_time_offset_hours", 0.0) or 0.0)
        df = shift_bar_times(
            load_bars(record["symbol"], record["timeframe"], date_from=date_from, date_to=date_to),
            bar_time_offset_hours,
        )
        intrabar_df = None
        if effective_intrabar_steps > 1 and str(record["timeframe"]).upper() != "M1":
            intrabar_df = shift_bar_times(
                load_bars(record["symbol"], "M1", date_from=date_from, date_to=date_to),
                bar_time_offset_hours,
            )
        param_grid = default_wfo_param_grid_for_template(
            str(record.get("template_name", "")),
            record.get("params", {}),
        )
        if not param_grid:
            param_grid = default_param_grid(record.get("params", {}))
        if param_grid:
            try:
                symbol_upper = str(record.get("symbol", "")).upper()
                is_crypto = any(c in symbol_upper for c in ["USDT", "BTC", "ETH", "SOL", "AVAX", "TAO", "XRP"])
                wfo = run_wfo(
                    strat_cls,
                    df,
                    param_grid=param_grid,
                    train_months=12,
                    test_months=3,
                    optimize_by="sharpe_ratio",
                    backtester_kwargs={
                        "initial_capital": 100_000,
                        "intrabar_steps": int(effective_intrabar_steps),
                        "commission_per_lot": float(execution_config["commission_per_lot"]),
                        "spread_pips": float(execution_config["spread_pips"]),
                        "slippage_pips": float(execution_config["slippage_pips"]),
                        "tick_size": float(execution_config.get("tick_size", 1.0)),
                        "tick_value": float(execution_config.get("tick_value", 0.0)),
                        "contract_size": float(execution_config.get("contract_size", 0.0)),
                        "swap_per_lot_long": float(execution_config.get("swap_per_lot_long", 0.0)),
                        "swap_per_lot_short": float(execution_config.get("swap_per_lot_short", 0.0)),
                        "swap_weekday_multipliers": dict(execution_config.get("swap_weekday_multipliers", {})),
                        "session_timezone_offset_hours": float(execution_config.get("session_timezone_offset_hours", 0.0)),
                        "use_bar_spread": bool(execution_config.get("use_bar_spread", False)),
                        "bar_spread_multiplier": float(execution_config.get("bar_spread_multiplier", 1.0)),
                        "tradable_session_windows": dict(execution_config.get("tradable_session_windows", {})),
                        "force_flat_weekday": int(execution_config.get("force_flat_weekday", -1)),
                        "force_flat_hhmm": str(execution_config.get("force_flat_hhmm", "")),
                        "is_crypto": is_crypto,
                    },
                    intrabar_df=intrabar_df,
                )
                evaluation["wfo"] = wfo.summary()
                evaluation["parameter_stability"] = {
                    "score": round(param_stability_score(wfo.params_used), 4),
                    "windows": len(wfo.params_used),
                }
                evaluation["wfo_param_grid"] = param_grid
            except Exception as exc:
                evaluation["wfo"] = {"error": str(exc)}
                evaluation["parameter_stability"] = {"score": 0.0, "windows": 0}
                evaluation["wfo_param_grid"] = param_grid
        else:
            evaluation["wfo"] = {}
            evaluation["parameter_stability"] = {"score": 1.0, "windows": 0}
            evaluation["wfo_param_grid"] = {}

    bt = evaluation["backtest"]
    mc = evaluation.get("monte_carlo", {})
    wfo = evaluation.get("wfo", {})
    stability = evaluation.get("parameter_stability", {}).get("score", 0.0)
    scoring_profile = resolve_scoring_profile(record)
    mt5_validation = record.get("mt5_validation", {}) if isinstance(record.get("mt5_validation", {}), dict) else {}
    mt5_comparison = mt5_validation.get("comparison", {}) if isinstance(mt5_validation.get("comparison", {}), dict) else {}
    mt5_corr_score = mt5_correlation_score(mt5_comparison)
    suspicious_val = suspicious_score(str(record.get("symbol", "")), bt, mt5_comparison)
    needs_mt5_validation = suspicious_val >= 0.35 and str(record.get("symbol", "")).strip().upper() in {"HK50.CASH", "US100.CASH", "US30.CASH", "UK100.CASH", "XAUUSD"}
    score, score_components, scoring_profile = score_candidate(
        template_name=str(record.get("template_name", "")),
        backtest=bt,
        wfo=wfo,
        monte_carlo=mc,
        stability_score=float(stability),
        scoring_profile=scoring_profile,
    )
    score += float(scoring_profile.get("mt5_corr_weight", 0.0)) * float(mt5_corr_score)
    score_components["mt5_correlation"] = round(float(scoring_profile.get("mt5_corr_weight", 0.0)) * float(mt5_corr_score), 4)
    suspicious_penalty = round(float(suspicious_val) * 15.0, 4)
    score -= suspicious_penalty
    score_components["suspicious_penalty"] = -float(suspicious_penalty)

    policy = resolve_promotion_policy(record)
    mc_prob_profit = float(mc.get("prob_profit", 0.0)) if isinstance(mc, dict) else 0.0
    wfo_robustness = float(wfo.get("robustness_score", 0.0)) if isinstance(wfo, dict) else 0.0
    requires_mt5_gate = str(record.get("symbol", "")).strip().upper() == "XAUUSD"
    mt5_ok = bool(mt5_validation.get("accepted", False)) if requires_mt5_gate else True
    mt5_correlation_ok = (
        float(mt5_corr_score) >= float(policy.get("min_mt5_correlation_score", 0.0))
        if mt5_comparison
        else (not requires_mt5_gate or not mt5_validation)
    )
    accepted = (
        bt.get("num_trades", 0) >= int(policy["min_trades"])
        and bt.get("profit_factor", 0.0) >= float(policy["min_profit_factor"])
        and bt.get("max_drawdown_pct", 100.0) <= float(policy["max_drawdown_pct"])
        and float(bt.get("win_rate", 0.0) or 0.0) >= float(policy.get("min_win_rate", 0.0))
        and (float(bt.get("max_recovery_days", 9999)) <= float(policy["max_stagnation_days"]) if "max_stagnation_days" in policy else True)
        and wfo_robustness >= float(policy["min_wfo_robustness"])
        and mc_prob_profit >= float(policy["min_mc_prob_profit"])
        and score >= float(policy["min_score"])
        and mt5_correlation_ok
        and mt5_ok
    )

    evaluation["score_components"] = score_components
    evaluation["score"] = round(score, 2)
    evaluation["scoring_profile"] = scoring_profile
    evaluation["accepted"] = bool(accepted)
    evaluation["promotion_policy"] = policy
    evaluation["mt5_correlation_score"] = round(float(mt5_corr_score), 4)
    evaluation["suspicious_score"] = round(float(suspicious_val), 4)
    evaluation["needs_mt5_validation"] = bool(needs_mt5_validation)
    evaluation["promotion_checks"] = {
        "trades_ok": bt.get("num_trades", 0) >= int(policy["min_trades"]),
        "profit_factor_ok": bt.get("profit_factor", 0.0) >= float(policy["min_profit_factor"]),
        "drawdown_ok": bt.get("max_drawdown_pct", 100.0) <= float(policy["max_drawdown_pct"]),
        "win_rate_ok": float(bt.get("win_rate", 0.0) or 0.0) >= float(policy.get("min_win_rate", 0.0)),
        "stagnation_ok": (float(bt.get("max_recovery_days", 9999)) <= float(policy["max_stagnation_days"]) if "max_stagnation_days" in policy else True),
        "wfo_ok": wfo_robustness >= float(policy["min_wfo_robustness"]),
        "mc_ok": mc_prob_profit >= float(policy["min_mc_prob_profit"]),
        "score_ok": score >= float(policy["min_score"]),
        "mt5_correlation_ok": mt5_correlation_ok,
        "mt5_ok": mt5_ok,
        "needs_mt5_validation": bool(needs_mt5_validation),
    }
    evaluation["intrabar_steps"] = int(effective_intrabar_steps)
    evaluation["mt5_gate_required"] = bool(requires_mt5_gate)

    record["evaluation"] = evaluation
    record["updated_at"] = utc_now()
    if accepted and record.get("status") == "draft":
        record["status"] = "candidate"
    upsert_native_strategy_record(record)
    return evaluation
