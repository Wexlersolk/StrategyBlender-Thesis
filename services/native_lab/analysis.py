from __future__ import annotations

from typing import Any

import pandas as pd

from engine.backtester import Backtester
from engine.data_loader import load_bars
from services.native_lab.config import (
    ENGINE_WARMUP_BARS,
    FAST_FILTER_TAIL_BARS,
    FAST_FILTER_TRADE_SAMPLE,
)
from services.native_lab.runtime import compile_runtime_strategy
from services.native_lab.utils import get_by_path, stable_hash
from services.backtest_service import resolve_execution_config
from services.python_strategy_service import strategy_spec_from_template


def structural_signature(template_name: str, payload: dict[str, Any]) -> str:
    normalized = str(template_name or "").strip()
    if normalized == "xau_discovery_grammar":
        keys = ("entry_archetype", "volatility_filter", "session_filter", "stop_model", "target_model", "exit_model", "direction_mode")
    elif normalized == "sqx_hk50_batch_h1":
        keys = (
            "long_signal_mode",
            "short_signal_mode",
            "params.LWMAPeriod1",
            "params.IndicatorCrsMAPrd1",
            "params.StopLossCoef1",
            "params.ProfitTargetCoef1",
            "params.StopLossCoef2",
            "params.ProfitTargetCoef2",
            "params.Highest_period",
            "params.Lowest_period",
            "params.SignalTimeRangeFrom",
            "params.SignalTimeRangeTo",
        )
    elif normalized == "sqx_hk50_ichi_heiken_h1":
        keys = (
            "params.IchimokuTenkanPrd1",
            "params.IchimokuKijunPeriod1",
            "params.IndicatorMAPeriod1",
            "params.Highest_period",
            "params.Lowest_period",
            "params.SignalTimeRangeFrom",
            "params.SignalTimeRangeTo",
        )
    elif normalized == "sqx_hk50_ichimoku_channel_h1":
        keys = (
            "params.IchimokuTenkanPrd1",
            "params.IchimokuKijunPeriod1",
            "params.IchimokuSenkouPrd1",
            "params.Highest_period",
            "params.Lowest_period",
            "params.EntryBufferATR",
            "params.ProfitTargetCoef1",
            "params.SignalTimeRangeFrom",
            "params.SignalTimeRangeTo",
        )
    elif normalized == "sqx_hk50_wavetrend_break_h1":
        keys = (
            "params.WaveTrendChannelLng1",
            "params.WaveTrendAverageLng1",
            "params.EMAPeriod1",
            "params.Highest_period",
            "params.Lowest_period",
            "params.SignalTimeRangeFrom",
            "params.SignalTimeRangeTo",
        )
    elif normalized == "sqx_hk50_pivot_kama_wavetrend_h1":
        keys = (
            "params.KAMAERPeriod1",
            "params.KAMAShortPeriod1",
            "params.KAMALongPeriod1",
            "params.WaveTrendChannelLng1",
            "params.WaveTrendAverageLng1",
            "params.PivotStartMinute",
            "params.Highest_period",
            "params.Lowest_period",
            "params.ProfitTargetCoef1",
            "params.SignalTimeRangeFrom",
            "params.SignalTimeRangeTo",
        )
    elif normalized == "sqx_us100_nasdaq_smma_keltner":
        keys = (
            "params.SMMAPeriod1",
            "params.EWMAPeriod1",
            "params.KCFastPeriod1",
            "params.KCSlowPeriod1",
            "params.PriceEntryMult1",
            "params.SignalTimeRangeFrom",
        )
    elif normalized == "sqx_us100_nasdaq_qqe":
        keys = (
            "params.QQERsiPeriod1",
            "params.QQERsiPeriod2",
            "params.SMAEntryPeriod1",
            "params.PriceEntryMult1",
            "params.PriceEntryMult2",
            "params.SignalTimeRangeFrom",
        )
    elif normalized == "sqx_us100_nasdaq_ichi_keltner":
        keys = (
            "params.SMMAPeriod1",
            "params.IchimokuTenkanPrd1",
            "params.IchimokuKijunPeriod1",
            "params.KeltnerChannelPrd1",
            "params.PriceEntryMult1",
            "params.PriceEntryMult2",
            "params.SignalTimeRangeFrom",
        )
    elif normalized == "sqx_us30_wpr_stoch":
        keys = (
            "params.WPRPeriod",
            "params.StochK",
            "params.HighestPeriod",
            "params.LowestPeriod",
            "params.SignalTimeRangeFrom",
        )
    elif normalized == "sqx_hk50_after_retest_h4":
        keys = ("trend_bias_mode", "entry_style")
    elif normalized == "sqx_hk50_before_retest_h4":
        keys = ("signal_mode", "entry_style")
    else:
        keys = tuple(sorted(key for key in payload.keys() if key != "name" and not isinstance(payload.get(key), dict)))
    structure = {key: get_by_path(payload, key) for key in keys}
    return stable_hash({"template": normalized, "structure": structure})


def archetype_bucket(template_name: str, payload: dict[str, Any]) -> str:
    normalized = str(template_name or "").strip()
    def _session_bucket(start: str, end: str) -> str:
        window = f"{start}-{end}"
        if window <= "00:20-00:35":
            return "opening"
        if window <= "00:35-01:00":
            return "delayed_open"
        if "13:00" <= start <= "16:00":
            return "ny_open"
        return "extended"

    if normalized == "xau_discovery_grammar":
        entry = str(payload.get("entry_archetype", "breakout_stop"))
        session = str(payload.get("session_filter", "london_ny"))
        if entry in {"breakout_stop", "breakout_close"}:
            return "breakout"
        if entry in {"ema_reclaim", "atr_pullback_limit", "pullback_trend", "session_reclaim"}:
            return "retest"
        if session in {"london_only", "ny_only"} and str(payload.get("target_model", "")) in {"trend_runner", "asymmetric_runner"}:
            return "session_continuation"
        return "session_fade"
    if normalized.startswith("sqx_us100_") or normalized == "sqx_us30_wpr_stoch":
        params = dict(payload.get("params", {}))
        start = str(params.get("SignalTimeRangeFrom", "00:00"))
        end = str(params.get("SignalTimeRangeTo", "23:59"))
        dist_val = float(params.get("PriceEntryMult1", params.get("StopLossCoef1", 1.0)))
        dist_mode = "tight" if dist_val < 1.5 else "loose"
        return f"index_sqx:{_session_bucket(start, end)}:{dist_mode}"
    if normalized == "sqx_hk50_batch_h1":
        params = dict(payload.get("params", {}))
        start = str(params.get("SignalTimeRangeFrom", "00:13"))
        end = str(params.get("SignalTimeRangeTo", "00:26"))
        return ":".join(
            [
                "batch",
                str(payload.get("long_signal_mode", "ao_cross")),
                str(payload.get("short_signal_mode", "lwma_cross")),
                _session_bucket(start, end),
            ]
        )
    if normalized == "sqx_hk50_ichi_heiken_h1":
        params = dict(payload.get("params", {}))
        return f"ichi_heiken:{_session_bucket(str(params.get('SignalTimeRangeFrom', '00:13')), str(params.get('SignalTimeRangeTo', '00:35')))}"
    if normalized == "sqx_hk50_ichimoku_channel_h1":
        params = dict(payload.get("params", {}))
        return f"ichi_channel:{_session_bucket(str(params.get('SignalTimeRangeFrom', '00:13')), str(params.get('SignalTimeRangeTo', '00:26')))}"
    if normalized == "sqx_hk50_wavetrend_break_h1":
        params = dict(payload.get("params", {}))
        return f"wavetrend_break:{_session_bucket(str(params.get('SignalTimeRangeFrom', '00:13')), str(params.get('SignalTimeRangeTo', '00:35')))}"
    if normalized == "sqx_hk50_pivot_kama_wavetrend_h1":
        params = dict(payload.get("params", {}))
        return f"pivot_kama_wt:{_session_bucket(str(params.get('SignalTimeRangeFrom', '00:13')), str(params.get('SignalTimeRangeTo', '00:26')))}"
    if normalized == "sqx_hk50_after_retest_h4":
        return "retest"
    if normalized == "sqx_hk50_before_retest_h4":
        return "session_fade"
    return "general"


def load_fast_filter_df(symbol: str, timeframe: str) -> pd.DataFrame | None:
    try:
        df = load_bars(symbol, timeframe)
    except Exception:
        return None
    if df.empty:
        return None
    return df.tail(FAST_FILTER_TAIL_BARS).copy()


def behavioral_fingerprint(payload: dict[str, Any], template_name: str, df: pd.DataFrame | None) -> str:
    if df is None or len(df) <= ENGINE_WARMUP_BARS + 5:
        return f"payload:{stable_hash({'template': template_name, 'payload': payload})}"
    spec = strategy_spec_from_template(template_name, payload)
    strategy_id = stable_hash({"template": template_name, "payload": payload})
    strat_cls = compile_runtime_strategy(spec, strategy_id)
    execution_config = resolve_execution_config(str(payload.get("symbol", "")))
    symbol_upper = str(payload.get("symbol", "")).upper()
    is_crypto = any(c in symbol_upper for c in ["USDT", "BTC", "ETH", "SOL", "AVAX", "TAO", "XRP"])
    result = Backtester(
        initial_capital=100_000,
        lot_value=getattr(strat_cls, "lot_value", 1.0),
        commission_per_lot=float(execution_config["commission_per_lot"]),
        spread_pips=float(execution_config["spread_pips"]),
        slippage_pips=float(execution_config["slippage_pips"]),
        tick_size=float(execution_config.get("tick_size", 1.0)),
        tick_value=float(execution_config.get("tick_value", 0.0)),
        contract_size=float(execution_config.get("contract_size", 0.0)),
        swap_per_lot_long=float(execution_config.get("swap_per_lot_long", 0.0)),
        swap_per_lot_short=float(execution_config.get("swap_per_lot_short", 0.0)),
        swap_weekday_multipliers=dict(execution_config.get("swap_weekday_multipliers", {})),
        session_timezone_offset_hours=float(execution_config.get("session_timezone_offset_hours", 0.0)),
        use_bar_spread=bool(execution_config.get("use_bar_spread", False)),
        bar_spread_multiplier=float(execution_config.get("bar_spread_multiplier", 1.0)),
        tradable_session_windows=dict(execution_config.get("tradable_session_windows", {})),
        force_flat_weekday=int(execution_config.get("force_flat_weekday", -1)),
        force_flat_hhmm=str(execution_config.get("force_flat_hhmm", "")),
        is_crypto=is_crypto,
    ).run(strat_cls(), df)
    trade_signature = [
        (
            int(trade.opened_bar),
            int(trade.closed_bar),
            trade.direction.value,
            str(trade.comment),
            round(float(trade.entry_price), 6),
            round(float(trade.exit_price), 6),
        )
        for trade in result.trades[:FAST_FILTER_TRADE_SAMPLE]
    ]
    fp_payload = {
        "trades": int(result.n_trades),
        "profit_factor": round(float(result.profit_factor), 6),
        "drawdown_pct": round(float(result.max_drawdown[1]), 6),
        "net_profit": round(float(result.net_profit), 2),
        "trade_signature": trade_signature,
    }
    if int(result.n_trades) == 0:
        fp_payload["payload_hash"] = stable_hash(payload)
    return stable_hash(fp_payload)


def fast_filter_behavioral_duplicates(
    candidates: list[dict[str, Any]],
    template_name: str,
    base_payload: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if base_payload:
        df = load_fast_filter_df(str(base_payload.get("symbol", "")), str(base_payload.get("timeframe", "")))
    else:
        df = None
    kept: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    seen_fingerprints: dict[str, str] = {}
    for candidate in candidates:
        fingerprint = behavioral_fingerprint(candidate["payload"], template_name, df)
        enriched = {
            **candidate,
            "behavioral_fingerprint": fingerprint,
        }
        if fingerprint in seen_fingerprints:
            enriched["duplicate_of"] = seen_fingerprints[fingerprint]
            duplicates.append(enriched)
            continue
        seen_fingerprints[fingerprint] = candidate["candidate_id"]
        kept.append(enriched)
    return kept, duplicates
