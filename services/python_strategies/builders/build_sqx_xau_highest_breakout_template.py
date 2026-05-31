from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_xau_highest_breakout",
    description="XAU highest-breakout family mined from SQX batch.",
    family="commodity_breakout",
    regime="Commodity breakout",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=32
)
def build_sqx_xau_highest_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "HighestPeriod": 245,
        "LowestPeriod": 245,
        "PullbackSignalPeriod": 10,
        "FastSMAPeriod": 10,
        "SignalMAPeriod": 57,
        "LWMAPeriod": 54,
        "ShortLWMAPeriod": 14,
        "SMMAPeriod": 30,
        "HAFloorMAPeriod": 67,
        "WaveTrendChannel": 9,
        "WaveTrendAverage": 21,
        "ATRLongStopPeriod": 14,
        "ATRLongTargetPeriod": 14,
        "ATRLongTrailPeriod": 40,
        "ATRShortStopPeriod": 14,
        "ATRShortTargetPeriod": 19,
        "LongStopATR": 2.0,
        "LongTargetATR": 3.5,
        "ShortStopATR": 1.5,
        "ShortTargetATR": 4.8,
        "LongExpiryBars": 10,
        "ShortExpiryBars": 18,
        "LongTrailATR": 1.0,
        "LongTrailActivationATR": 0.0,
        "ShortTrailATR": 0.0,
        "ShortTrailActivationATR": 0.0,
        "HourQuantileLookback": 809,
        "HourQuantileThreshold": 66.5,
        "MaxDistancePct": 6.0,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    direction_mode = _direction_mode(payload)

    long_signal_mode = str(payload.get("long_signal_mode", "sma_bias"))
    short_signal_mode = str(payload.get("short_signal_mode", "lwma_lowest_count"))

    long_signal_map = {
        "sma_bias": 'df["sma_fast"].shift(3) > df["sma_fast"].shift(3).rolling(int(self.p("SignalMAPeriod")), min_periods=5).mean()',
        "smma_pullback": 'df["low"].rolling(int(self.p("PullbackSignalPeriod")), min_periods=2).min().shift(3) <= df["smma_mid"].shift(2)',
        "ha_reclaim": 'df["ha_floor"].shift(1) > df["ha_floor"].shift(1).rolling(int(self.p("HAFloorMAPeriod")), min_periods=5).mean()',
    }
    short_signal_map = {
        "lwma_lowest_count": '_sq_count_compare(df["lwma_fast"], df["lowest_typical"].shift(2), 2, 1, greater=False, not_strict=True)',
        "wt_push": '(df["close"].shift(1) > df["smma_mid"].shift(1)) & _rising(df["wt_main"], 2, 1)',
        "lwma_hour_quantile": '(df["lwma_short"].shift(1) > df["low"].shift(2)) & (df["hour_ref"].shift(3) <= df["hour_ref"].shift(3).rolling(int(self.p("HourQuantileLookback")), min_periods=25).quantile(float(self.p("HourQuantileThreshold")) / 100.0))',
    }
    long_signal = long_signal_map.get(long_signal_mode, long_signal_map["sma_bias"])
    short_signal = short_signal_map.get(short_signal_mode, short_signal_map["lwma_lowest_count"])

    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_highest_breakout_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo"))) and (abs(float(ctx.open) - float(df["highest_level"].iloc[i])) / max(float(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))',
                price='float(df["highest_level"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest_level"].iloc[i]) - float(self.p("LongStopATR")) * float(df["atr_long_stop"].iloc[i - 1])',
                take_profit='float(df["highest_level"].iloc[i]) + float(self.p("LongTargetATR")) * float(df["atr_long_target"].iloc[i - 1])',
                trail_dist='float(self.p("LongTrailATR")) * float(df["atr_long_trail"].iloc[i - 1])',
                trail_activation='float(self.p("LongTrailActivationATR")) * float(df["atr_long_trail"].iloc[i - 1])',
                expiry_bars=int(params.get("LongExpiryBars", 10)),
                comment="sqx_xau_highest_breakout_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_highest_breakout_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo"))) and (abs(float(ctx.open) - float(df["lowest_level"].iloc[i-1])) / max(float(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))',
                price='float(df["lowest_level"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest_level"].iloc[i-1]) + float(self.p("ShortStopATR")) * float(df["atr_short_stop"].iloc[i - 1])',
                take_profit='float(df["lowest_level"].iloc[i-1]) - float(self.p("ShortTargetATR")) * float(df["atr_short_target"].iloc[i - 1])',
                trail_dist='float(self.p("ShortTrailATR")) * float(df["atr_short_target"].iloc[i - 1])',
                trail_activation='float(self.p("ShortTrailActivationATR")) * float(df["atr_short_target"].iloc[i - 1])',
                expiry_bars=int(params.get("ShortExpiryBars", 18)),
                comment="sqx_xau_highest_breakout_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 80)),
        lot_value=float(payload.get("lot_value", 100.0)),
        bar_time_offset_hours=float(payload.get("bar_time_offset_hours", 6.0)),
        description=payload.get(
            "description",
            "SQX-inspired XAU highest-breakout family mined from Batch12.04, with stop entries and ATR-managed exits.",
        ),
        indicators=[
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 2}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 3}),
            IndicatorSpec("typical_price", "select_price", {"open_": "open", "high": "high", "low": "low", "close": "close", "mode": 5}),
            IndicatorSpec("sma_fast", "sma", {"series": "close", "period": {"param": "FastSMAPeriod"}}),
            IndicatorSpec("lwma_fast", "wma", {"series": "close", "period": {"param": "LWMAPeriod"}}),
            IndicatorSpec("lwma_short", "wma", {"series": "close", "period": {"param": "ShortLWMAPeriod"}}),
            IndicatorSpec("smma_mid", "smma", {"series": "typical_price", "period": {"param": "SMMAPeriod"}}),
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "close": "ha_close"}),
            IndicatorSpec("wt", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrendChannel"}, "average_length": {"param": "WaveTrendAverage"}}, outputs={"main": "wt_main"}),
            IndicatorSpec("atr_long_stop", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRLongStopPeriod"}}),
            IndicatorSpec("atr_long_target", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRLongTargetPeriod"}}),
            IndicatorSpec("atr_long_trail", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRLongTrailPeriod"}}),
            IndicatorSpec("atr_short_stop", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRShortStopPeriod"}}),
            IndicatorSpec("atr_short_target", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRShortTargetPeriod"}}),
        ],
        series=[
            SeriesSpec("lowest_typical", 'df["typical_price"].rolling(int(self.p("PullbackSignalPeriod")), min_periods=2).min()'),
            SeriesSpec("ha_floor", 'df[["low", "ha_open", "ha_close"]].min(axis=1)'),
            SeriesSpec("hour_ref", 'df.index.to_series().dt.hour.astype(float)'),
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=entries,
    )
