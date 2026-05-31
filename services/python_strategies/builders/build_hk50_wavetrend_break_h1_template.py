from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_wavetrend_break_h1",
    description="HK50 H1 WaveTrend breakout family.",
    family="index_wavetrend_breakout",
    regime="Index WaveTrend breakout continuation",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=72
)
def build_hk50_wavetrend_break_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "WaveTrendChannelLng1": 14,
        "WaveTrendAverageLng1": 21,
        "EMAPeriod1": 40,
        "Highest_period": 35,
        "Lowest_period": 35,
        "ATRFastPeriod": 14,
        "ATRSlowPeriod": 19,
        "StopLossCoef1": 2.1,
        "ProfitTargetCoef1": 5.2,
        "StopLossCoef2": 2.2,
        "ProfitTargetCoef2": 3.0,
        "TrailingStop1": 155.0,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:35",
        "FridayExitTime": "22:38",
        "mmLots": 45.0,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 55)),
        lot_value=float(payload.get("lot_value", 0.1285)),
        description=payload.get("description", "HK50 H1 WaveTrend breakout family mined from Batch1 WaveTrend winners."),
        indicators=[
            IndicatorSpec("wt", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrendChannelLng1"}, "average_length": {"param": "WaveTrendAverageLng1"}}, outputs={"main": "wt_main"}),
            IndicatorSpec("ema_bias", "ema", {"series": "close", "period": {"param": "EMAPeriod1"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": 0}),
            IndicatorSpec("atr_fast", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRFastPeriod"}}),
            IndicatorSpec("atr_slow", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRSlowPeriod"}}),
        ],
        series=[
            SeriesSpec("long_signal", '(df["wt_main"].shift(1) > 0.0) & (df["close"].shift(1) > df["ema_bias"].shift(1)) & _rising(df["close"], 2, 2)'),
            SeriesSpec("short_signal", '(df["wt_main"].shift(1) < 0.0) & (df["close"].shift(1) < df["ema_bias"].shift(1)) & _falling(df["close"], 2, 2)'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_wavetrend_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i]) - (float(self.p("StopLossCoef1")) * float(df["atr_fast"].iloc[i]))',
                take_profit='float(df["highest"].iloc[i]) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_slow"].iloc[i]))',
                trail_dist='float(self.p("TrailingStop1"))',
                expiry_bars=1,
                comment="hk50_wavetrend_long",
            ),
            EntryRuleSpec(
                name="hk50_wavetrend_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i]) + (float(self.p("StopLossCoef2")) * float(df["atr_fast"].iloc[i]))',
                take_profit='float(df["lowest"].iloc[i]) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_slow"].iloc[i]))',
                trail_dist='float(self.p("TrailingStop1"))',
                expiry_bars=1,
                comment="hk50_wavetrend_short",
            ),
        ],
    )
