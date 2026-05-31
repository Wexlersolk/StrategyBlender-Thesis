from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_xau_ao_hour_breakout",
    description="XAU AO hour-breakout family mined from SQX batch.",
    family="commodity_breakout_momentum",
    regime="Commodity momentum breakout",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=33
)
def build_sqx_xau_ao_hour_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "LWMAPeriod1": 40,
        "IndicatorMAPeriod1": 67,
        "AOPercentile": 48.9,
        "AOPercentileLookback": 829,
        "AskPercentile": 37.3,
        "AskPercentileLookback": 841,
        "HighestPeriod": 200,
        "LowestPeriod": 200,
        "ATRPeriod": 19,
        "ProfitTargetCoef1": 5.0,
        "StopLossCoef1": 2.2,
        "TrailingStop1": 155.0,
        "ProfitTargetCoef2": 3.0,
        "StopLossCoef2": 1.8,
        "LongExpiryBars": 20,
        "ShortExpiryBars": 14,
        "TickSize": 0.01,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
        "FridayExitTime": "22:38",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    direction_mode = _direction_mode(payload)

    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_ao_hour_breakout_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and not bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest_level"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest_level"].iloc[i]) - (float(self.p("StopLossCoef1")) * float(df["atr_1"].iloc[i - 1]))',
                take_profit='float(df["highest_level"].iloc[i]) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_1"].iloc[i - 1]))',
                trail_dist='float(self.p("TrailingStop1")) * float(self.p("TickSize"))',
                expiry_bars=int(params.get("LongExpiryBars", 20)),
                comment="sqx_xau_ao_hour_breakout_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_ao_hour_breakout_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest_level"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest_level"].iloc[i]) + (float(self.p("StopLossCoef2")) * float(df["atr_1"].iloc[i - 1]))',
                take_profit='float(df["lowest_level"].iloc[i]) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_1"].iloc[i - 1]))',
                expiry_bars=int(params.get("ShortExpiryBars", 14)),
                comment="sqx_xau_ao_hour_breakout_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 900)),
        lot_value=float(payload.get("lot_value", 100.0)),
        bar_time_offset_hours=float(payload.get("bar_time_offset_hours", 6.0)),
        description=payload.get(
            "description",
            "Native Batch3-derived XAU breakout family from Strategy 5.4.86(1), using AO percentile and hour/ask percentile asymmetry with ATR-managed stop entries.",
        ),
        indicators=[
            IndicatorSpec("ao", "sq_awesome_oscillator", {"high": "high", "low": "low", "fast_period": 5, "slow_period": 34}),
            IndicatorSpec("lwma_open", "wma", {"series": "open", "period": {"param": "LWMAPeriod1"}}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 0}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 0}),
        ],
        series=[
            SeriesSpec("hour_ref", 'df.index.to_series().dt.hour.astype(float)'),
            SeriesSpec("ask_proxy", 'df["open"] + (df.get("spread", pd.Series(0.0, index=df.index)).astype(float) * float(self.p("TickSize")))'),
            SeriesSpec("hour_sma", 'df["hour_ref"].shift(3).rolling(int(self.p("IndicatorMAPeriod1")), min_periods=int(self.p("IndicatorMAPeriod1"))).mean()'),
            SeriesSpec("long_signal", '_sq_lower_percentile(df["ao"], float(self.p("AOPercentile")), int(self.p("AOPercentileLookback")), 3, rounding=5) & (df["high"].shift(1).round(6) > df["lwma_open"].shift(1).round(6))'),
            SeriesSpec("short_signal", '(df["hour_ref"].shift(3).round(6) > df["hour_sma"].round(6)) & _sq_lower_percentile(df["ask_proxy"], float(self.p("AskPercentile")), int(self.p("AskPercentileLookback")), 1, rounding=5)'),
        ],
        exits=[
            ExitRuleSpec(
                "friday_exit",
                'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))',
            ),
        ],
        entries=entries,
    )
