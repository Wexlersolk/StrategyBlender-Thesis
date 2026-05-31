from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_pivot_kama_wavetrend_h1",
    description="HK50 H1 pivot plus KAMA plus WaveTrend breakout family.",
    family="index_pivot_kama_breakout",
    regime="Index pivot KAMA WaveTrend breakout",
    supported_symbols=("HK50.cash", "GER40.cash", "US30.cash", "US100.cash", "AUDUSD"),
    supported_timeframes=("M30", "H1", "H4"),
    preferred_timeframes=("M30", "H1", "H4"),
    sort_order=74
)
def build_hk50_pivot_kama_wavetrend_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "KAMAERPeriod1": 100,
        "KAMAShortPeriod1": 56,
        "KAMALongPeriod1": 27,
        "WaveTrendChannelLng1": 53,
        "WaveTrendAverageLng1": 21,
        "WaveTrendSignalLng1": 4,
        "PivotStartHour": 0,
        "PivotStartMinute": 20,
        "Highest_period": 90,
        "Lowest_period": 60,
        "ATRFastPeriod": 14,
        "ATRTrailPeriod": 100,
        "ATRSlowPeriod": 19,
        "StopLossCoef1": 1.6,
        "ProfitTargetCoef1": 1.9,
        "TrailingStopCoef1": 1.0,
        "StopLossCoef2": 2.7,
        "ProfitTargetCoef2": 2.2,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:26",
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
        min_bars=int(payload.get("min_bars", 60)),
        lot_value=float(payload.get("lot_value", 0.1285)),
        description=payload.get("description", "HK50 H1 pivot plus KAMA plus WaveTrend breakout family mined from SQX winners."),
        indicators=[
            IndicatorSpec("kama", "sq_kama", {"close": "close", "er_period": {"param": "KAMAERPeriod1"}, "fast_period": {"param": "KAMAShortPeriod1"}, "slow_period": {"param": "KAMALongPeriod1"}}),
            IndicatorSpec("wt", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrendChannelLng1"}, "average_length": {"param": "WaveTrendAverageLng1"}, "signal_length": {"param": "WaveTrendSignalLng1"}}, outputs={"main": "wt_main", "signal": "wt_signal"}),
            IndicatorSpec("pivots", "sq_pivots", {"df": "df", "start_hour": {"param": "PivotStartHour"}, "start_minute": {"param": "PivotStartMinute"}}, outputs={"pp": "pivot_pp", "r1": "pivot_r1", "s1": "pivot_s1"}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": 0}),
            IndicatorSpec("atr_fast", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRFastPeriod"}}),
            IndicatorSpec("atr_slow", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRSlowPeriod"}}),
            IndicatorSpec("atr_trail", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRTrailPeriod"}}),
        ],
        series=[
            SeriesSpec("long_signal", '(df["wt_main"].shift(1) > df["wt_signal"].shift(1)) & (df["close"].shift(1) > df["kama"].shift(1)) & (df["close"].shift(1) > df["pivot_pp"].shift(1))'),
            SeriesSpec("short_signal", '(df["wt_main"].shift(1) < df["wt_signal"].shift(1)) & (df["close"].shift(1) < df["kama"].shift(1)) & (df["close"].shift(1) < df["pivot_pp"].shift(1))'),
            SeriesSpec("long_exit_signal", 'df["close"].shift(1) < df["kama"].shift(1)'),
            SeriesSpec("short_exit_signal", 'df["close"].shift(1) > df["kama"].shift(1)'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
            ExitRuleSpec("long_exit", 'ctx.has_long and bool(df["long_exit_signal"].eq(True).iloc[i])'),
            ExitRuleSpec("short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_pivot_kama_wt_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i]) - (float(self.p("StopLossCoef1")) * float(df["atr_fast"].iloc[i]))',
                take_profit='float(df["highest"].iloc[i]) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_fast"].iloc[i]))',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr_trail"].iloc[i])',
                expiry_bars=1,
                comment="hk50_pivot_kama_wt_long",
            ),
            EntryRuleSpec(
                name="hk50_pivot_kama_wt_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i]) + (float(self.p("StopLossCoef2")) * float(df["atr_fast"].iloc[i]))',
                take_profit='float(df["lowest"].iloc[i]) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_slow"].iloc[i]))',
                expiry_bars=1,
                comment="hk50_pivot_kama_wt_short",
            ),
        ],
    )
