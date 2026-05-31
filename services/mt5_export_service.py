from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.native_strategy_lab import get_native_strategy_record
from services.mt5_export.utils import mt5_output_dir
from services.mt5_export import renderers
from services.python_strategy_service import template_supports_market

RENDERER_MAP = {
    "sqx_xau_highest_breakout": renderers.render_sqx_xau_highest_breakout_ea,
    "hk50_h4_breakout": renderers.render_hk50_h4_breakout_ea,
    "sqx_batch": renderers.render_sqx_batch_ea,
    "sqx_xau_ao_hour_breakout": renderers.render_sqx_xau_ao_hour_breakout_ea,
    "sqx_xau_short_keltner_breakout": renderers.render_sqx_xau_short_keltner_breakout_ea,
    "sqx_hk50_batch_h1": renderers.render_sqx_hk50_batch_h1_ea,
    "sqx_hk50_ichi_heiken_h1": renderers.render_sqx_hk50_ichi_heiken_h1_ea,
    "sqx_hk50_wavetrend_break_h1": renderers.render_sqx_hk50_wavetrend_break_h1_ea,
    "sqx_hk50_ichimoku_channel_h1": renderers.render_sqx_hk50_ichimoku_channel_h1_ea,
    "sqx_hk50_pivot_kama_wavetrend_h1": renderers.render_sqx_hk50_pivot_kama_wavetrend_h1_ea,
    "sqx_hk50_reversion_h1": renderers.render_sqx_hk50_reversion_h1_ea,
    "sqx_us100_reversion_h1": renderers.render_sqx_us100_reversion_h1_ea,
    "sqx_us30_wpr_stoch": renderers.render_sqx_us30_wpr_stoch_ea,
    "sqx_us100_nasdaq_smma_keltner": renderers.render_sqx_us100_nasdaq_smma_keltner_ea,
    "sqx_us100_nasdaq_qqe": renderers.render_sqx_us100_nasdaq_qqe_ea,
    "sqx_us100_nasdaq_ichi_keltner": renderers.render_sqx_us100_nasdaq_ichi_keltner_ea,
    "sqx_uk100_ulcer_keltner_h1": renderers.render_sqx_uk100_ulcer_keltner_h1_ea,
    "sqx_usdjpy_vwap_wt": renderers.render_sqx_usdjpy_vwap_wt_ea,
    "sqx_usdjpy_ichi_keltner": renderers.render_sqx_usdjpy_ichi_keltner_ea,
    "sqx_usdjpy_dual_ema_rsi": renderers.render_sqx_usdjpy_dual_ema_rsi_ea,
    "sqx_index_h4_trend_reclaim": renderers.render_sqx_index_h4_trend_reclaim_ea,
    "sqx_gold_h4_ichi_momentum": renderers.render_sqx_gold_h4_ichi_momentum_ea,
    "sqx_fx_h4_swing_reversion": renderers.render_sqx_fx_h4_swing_reversion_ea,
    "sqx_hk50_after_retest_h4": renderers.render_sqx_hk50_after_retest_h4_ea,
    "breakout_confirm": renderers.render_breakout_confirm_ea,
    "trend_pullback": renderers.render_trend_pullback_ea,
    "reversion": renderers.render_reversion_ea,
    "xau_discovery_grammar": renderers.render_xau_discovery_ea,
    "xau_breakout_session": renderers.render_xau_discovery_ea,
    "session_breakout_extreme": renderers.render_session_breakout_extreme_ea,
    "us100_ny_momentum_v3": renderers.render_us100_ny_momentum_v3_ea,
    "ger40_m15_specialist": renderers.render_ger40_specialist_ea,
    "ger40_h4_pure_breakout": renderers.render_ger40_h4_breakout_ea,
    "xau_h4_regime_filtered": renderers.render_breakout_confirm_ea,
}


def export_native_strategy_to_mt5(
    strategy_id: str,
    *,
    output_name: str | None = None,
    collection: str | None = None,
    timeframe_override: str | None = None,
    extra_payload_updates: dict[str, Any] | None = None,
) -> dict[str, str]:
    record = get_native_strategy_record(strategy_id)
    if not record:
        raise ValueError(f"Unknown native strategy: {strategy_id}")

    template_name = str(record.get("template_name", ""))
    payload = dict(record.get("template_payload", {}))
    if timeframe_override:
        payload["timeframe"] = timeframe_override
    if extra_payload_updates:
        payload.update(extra_payload_updates)
    symbol = str(payload.get("symbol", ""))
    timeframe = str(payload.get("timeframe", ""))

    # if not template_supports_market(template_name, symbol, timeframe):
    #     raise ValueError(
    #         f"Template {template_name} is not supported for {symbol} {timeframe}; refusing MT5 export for an incompatible discovery candidate"
    #     )

    if template_name == "xau_discovery_grammar":
        entry_archetype = str(payload.get("entry_archetype", ""))
        volatility_filter = str(payload.get("volatility_filter", ""))
        session_filter = str(payload.get("session_filter", ""))
        stop_model = str(payload.get("stop_model", ""))
        target_model = str(payload.get("target_model", ""))
        if (
            entry_archetype == "atr_pullback_limit"
            or (session_filter == "london_only" and volatility_filter == "none")
            or (session_filter == "london_only" and stop_model == "swing")
            or (session_filter == "london_only" and target_model == "fixed_rr")
        ):
            raise ValueError("Rejected XAU export region: native payload is in a banned high-mismatch discovery block")

    renderer = RENDERER_MAP.get(template_name)
    if not renderer:
        raise ValueError(f"MT5 exporter does not support template: {template_name}")

    strategy_slug = output_name or strategy_id
    source = renderer(strategy_slug, payload)

    out_dir = mt5_output_dir(payload.get("symbol"), payload.get("timeframe"), strategy_slug, collection=collection)
    report_dir = out_dir / "ReportMT5"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    ea_path = out_dir / f"{strategy_slug}.mq5"
    ea_path.write_text(source, encoding="utf-8")

    spec_dump = out_dir / f"{strategy_slug}.native_payload.json"
    spec_dump.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    gitkeep = report_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")

    return {
        "strategy_id": strategy_id,
        "ea_path": str(ea_path),
        "report_dir": str(report_dir),
        "payload_path": str(spec_dump),
        "collection": str(collection or "generated"),
    }
