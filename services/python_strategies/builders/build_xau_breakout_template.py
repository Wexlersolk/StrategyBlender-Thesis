from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="xau_breakout_session",
    description="XAU session breakout with trend confirmation.",
    family="commodity_breakout",
    regime="Commodity session breakout",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=31
)
def build_xau_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "HighestPeriod": 24,
        "LowestPeriod": 24,
        "ATRPeriod": 14,
        "BBWRPeriod": 24,
        "BBWRMin": 0.015,
        "EntryBufferATR": 0.15,
        "StopLossATR": 1.4,
        "ProfitTargetATR": 2.8,
        "MaxDistancePct": 3.5,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "06:00",
        "SignalTimeRangeTo": "18:00",
        "ExitAfterBars": 18,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)

    direction_mode = _direction_mode(payload)
    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="xau_breakout_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["volatility_ok"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo"))) and bool(df["long_signal"].eq(True).iloc[i]) and (abs(float(ctx.open) - float(df["highest_level"].iloc[i])) / max(float(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))',
                price='float(df["highest_level"].iloc[i]) + (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["highest_level"].iloc[i]) + (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))) - (float(df["atr"].iloc[i - 1]) * float(self.p("StopLossATR")))',
                take_profit='(float(df["highest_level"].iloc[i]) + (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))) + (float(df["atr"].iloc[i - 1]) * float(self.p("ProfitTargetATR")))',
                expiry_bars=3,
                exit_after_bars='int(self.p("ExitAfterBars"))',
                comment="xau_breakout_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="xau_breakout_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["volatility_ok"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo"))) and bool(df["short_signal"].eq(True).iloc[i]) and (abs(float(ctx.open) - float(df["lowest_level"].iloc[i])) / max(float(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))',
                price='float(df["lowest_level"].iloc[i]) - (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["lowest_level"].iloc[i]) - (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))) + (float(df["atr"].iloc[i - 1]) * float(self.p("StopLossATR")))',
                take_profit='(float(df["lowest_level"].iloc[i]) - (float(df["atr"].iloc[i - 1]) * float(self.p("EntryBufferATR")))) - (float(df["atr"].iloc[i - 1]) * float(self.p("ProfitTargetATR")))',
                expiry_bars=3,
                exit_after_bars='int(self.p("ExitAfterBars"))',
                comment="xau_breakout_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 30)),
        lot_value=float(payload.get("lot_value", 100.0)),
        description=payload.get("description", "XAU volatility breakout with ATR buffer and session gating."),
        indicators=[
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 2}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 3}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
            IndicatorSpec("bbwr", "sq_bb_width_ratio", {"series": "close", "period": {"param": "BBWRPeriod"}, "deviations": 2.0}),
        ],
        series=[
            SeriesSpec("volatility_ok", 'df["bbwr"] >= float(self.p("BBWRMin"))'),
            SeriesSpec("long_signal", 'df["close"] > df["highest_level"].shift(1)'),
            SeriesSpec("short_signal", 'df["close"] < df["lowest_level"].shift(1)'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=entries,
    )
