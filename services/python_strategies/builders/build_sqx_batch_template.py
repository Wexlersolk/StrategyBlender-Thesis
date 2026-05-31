from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_batch",
    description="Generic StrategyQuant Batch template with cross-symbol flexibility.",
    family="batch_breakout",
    regime="Session breakout and momentum",
    supported_symbols=("USDJPY", "HK50.cash", "XAUUSD", "US100.cash", "US30.cash", "UK100.cash", "GER40.cash", "GBPJPY", "XAGUSD", "AUDUSD", "USDCAD", "USNGAS.CASH"),
    supported_timeframes=("M30", "H1", "H4"),
    preferred_timeframes=("M30", "H1", "H4"),
    sort_order=90
)
def build_sqx_batch_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "mmLots": 1.0,
        "StopLossCoef1": 2.5,
        "ProfitTargetCoef1": 3.5,
        "TrailingActCef1": 1.5,
        "TrailingStop1": 150.0,
        "StopLossCoef2": 2.5,
        "ProfitTargetCoef2": 3.5,
        "TrailingStopCoef1": 1.0,
        "IndicatorCrsMAPrd1": 50,
        "IndicatorCrsMAPrd2": 50,
        "ATR1_period": 14,
        "ATR2_period": 20,
        "ATR3_period": 14,
        "ATR4_period": 50,
        "Highest_period": 20,
        "Lowest_period": 20,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
        "TickSize": 0.001,
    }
    
    # Adaptive TickSize based on symbol if not provided in payload
    normalized_symbol = _canonical_symbol(symbol).upper()
    if "GER40" in normalized_symbol:
        defaults["TickSize"] = 0.1
    elif "US30" in normalized_symbol:
        defaults["TickSize"] = 1.0
    elif "US100" in normalized_symbol or "HK50" in normalized_symbol or "XAU" in normalized_symbol:
        defaults["TickSize"] = 0.01

    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal_mode = str(payload.get("long_signal_mode", "cross_above"))
    short_signal_mode = str(payload.get("short_signal_mode", "cross_below"))
    
    if long_signal_mode == "cross_above":
        long_signal = '_cross_above(df["main_ind"], df["signal_ind"])'
    elif long_signal_mode == "rising":
        long_signal = '_rising(df["main_ind"], 2, 1)'
    else:
        long_signal = 'df["main_ind"] > df["signal_ind"]'
        
    if short_signal_mode == "cross_below":
        short_signal = '_cross_below(df["main_ind"], df["signal_ind"])'
    elif short_signal_mode == "falling":
        short_signal = '_falling(df["main_ind"], 2, 1)'
    else:
        short_signal = 'df["main_ind"] < df["signal_ind"]'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 100)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "Generic SQX Batch template for cross-symbol generation."),
        indicators=[
            IndicatorSpec("main_ind", "ema", {"series": "close", "period": {"param": "IndicatorCrsMAPrd1"}}),
            IndicatorSpec("signal_ind", "sma", {"series": "main_ind", "period": {"param": "IndicatorCrsMAPrd2"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": 2}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": 3}),
            IndicatorSpec("atr1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR1_period"}}),
            IndicatorSpec("atr2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR2_period"}}),
            IndicatorSpec("atr3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR3_period"}}),
            IndicatorSpec("atr4", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR4_period"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="batch_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i - 1]) - float(self.p("StopLossCoef1")) * float(df["atr1"].iloc[i - 1])',
                take_profit='float(df["highest"].iloc[i - 1]) + float(self.p("ProfitTargetCoef1")) * float(df["atr2"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr4"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr3"].iloc[i - 1])',
                expiry_bars=5,
                comment="batch_long",
            ),
            EntryRuleSpec(
                name="batch_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i - 1]) + float(self.p("StopLossCoef2")) * float(df["atr1"].iloc[i - 1])',
                take_profit='float(df["lowest"].iloc[i - 1]) - float(self.p("ProfitTargetCoef2")) * float(df["atr2"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr4"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr3"].iloc[i - 1])',
                expiry_bars=5,
                comment="batch_short",
            ),
        ],
    )
