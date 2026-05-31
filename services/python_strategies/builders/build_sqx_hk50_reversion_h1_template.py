from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_reversion_h1",
    description="High-win-rate HK50 mean-reversion using BB and WPR.",
    family="index_reversion",
    regime="Index mean-reversion",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=10
)
def build_sqx_hk50_reversion_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "BBPeriod1": 20,
        "BBDev1": 2.0,
        "WPRPeriod1": 14,
        "WPRUpper": -20.0,
        "WPRLower": -80.0,
        "ATRPeriod1": 14,
        "StopLossCoef1": 1.5,
        "ProfitTargetCoef1": 1.2,
        "mmLots": 45.0,
        "SignalTimeRangeFrom": "04:25",
        "SignalTimeRangeTo": "11:00",
        "FridayExitTime": "11:30",
    }
    for k, v in defaults.items():
        params.setdefault(k, v)

    direction_mode = _direction_mode(payload)
    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="hk50_reversion_long",
                side="long",
                order_type="market",
                when='(df["close"].shift(1) < df["bb_lower"].shift(1)) & (df["wpr"].shift(1) < float(self.p("WPRLower"))) & _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='float(ctx.open) - (float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i]))',
                take_profit='float(ctx.open) + (float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i]))',
                comment="hk50_reversion_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="hk50_reversion_short",
                side="short",
                order_type="market",
                when='(df["close"].shift(1) > df["bb_upper"].shift(1)) & (df["wpr"].shift(1) > float(self.p("WPRUpper"))) & _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='float(ctx.open) + (float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i]))',
                take_profit='float(ctx.open) - (float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i]))',
                comment="hk50_reversion_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        indicators=[
            IndicatorSpec("bb", "sq_bollinger_bands", {"close": "close", "period": {"param": "BBPeriod1"}, "deviations": {"param": "BBDev1"}}, outputs={"lower": "bb_lower", "upper": "bb_upper"}),
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPRPeriod1"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
        ],
        exits=[
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
        ],
        entries=entries,
    )
