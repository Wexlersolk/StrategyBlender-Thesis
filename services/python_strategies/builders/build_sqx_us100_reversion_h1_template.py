from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_us100_reversion_h1",
    description="High-win-rate US100 mean-reversion using BB and WPR.",
    family="index_reversion",
    regime="Index mean-reversion",
    supported_symbols=("US100.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=11
)
def build_sqx_us100_reversion_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "BBPeriod1": 34,
        "BBDev1": 2.2,
        "WPRPeriod1": 21,
        "WPRUpper": -15.0,
        "WPRLower": -85.0,
        "ATRPeriod1": 14,
        "StopLossCoef1": 2.5,
        "ProfitTargetCoef1": 1.8,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "01:00",
        "SignalTimeRangeTo": "22:00",
        "FridayExitTime": "22:30",
    }
    for k, v in defaults.items():
        params.setdefault(k, v)

    direction_mode = _direction_mode(payload)
    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="us100_reversion_long",
                side="long",
                order_type="market",
                when='bool(df["long_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='float(ctx.open) - (float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i]))',
                take_profit='float(ctx.open) + (float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i]))',
                comment="us100_reversion_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="us100_reversion_short",
                side="short",
                order_type="market",
                when='bool(df["short_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='float(ctx.open) + (float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i]))',
                take_profit='float(ctx.open) - (float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i]))',
                comment="us100_reversion_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        indicators=[
            IndicatorSpec("bb", "bollinger_bands", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "BBPeriod1"}, "deviations": {"param": "BBDev1"}, "mode": 0}, outputs={"lower": "bb_lower", "upper": "bb_upper"}),
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPRPeriod1"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
        ],
        series=[
            SeriesSpec("long_signal", '(df["close"].shift(1) < df["bb_lower"].shift(1)) & (df["wpr"].shift(1) < float(self.p("WPRLower")))'),
            SeriesSpec("short_signal", '(df["close"].shift(1) > df["bb_upper"].shift(1)) & (df["wpr"].shift(1) > float(self.p("WPRUpper")))'),
        ],
        exits=[
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
        ],
        entries=entries,
    )
