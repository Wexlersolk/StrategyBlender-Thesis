from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_m15_momentum",
    description="HK50 M15 Momentum Breakout using WaveTrend and EMA for the HK Open.",
    family="hk50_momentum",
    regime="M15 Intraday Momentum",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("M15",),
    preferred_timeframes=("M15",),
    sort_order=86
)
def build_hk50_m15_momentum_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "EMA_period": 100,
        "WaveTrend_ch_len": 9,
        "WaveTrend_avg_len": 21,
        "ATR_period": 14,
        "ATR_SL_multiplier": 2.0,
        "ATR_TP_multiplier": 3.0,
        "SignalTimeRangeFrom": "01:15",
        "SignalTimeRangeTo": "04:30",
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal = '(df["wt_main"] > df["wt_signal"]) & (df["close"] > df["ema"]) & (df["wt_main"] < 40)'
    short_signal = '(df["wt_main"] < df["wt_signal"]) & (df["close"] < df["ema"]) & (df["wt_main"] > -40)'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=250,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="HK50 M15 Momentum Breakout.",
        indicators=[
            IndicatorSpec("ema", "ema", {"series": "close", "period": {"param": "EMA_period"}}),
            IndicatorSpec(
                "wt_res", "sq_wave_trend", 
                {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrend_ch_len"}, "average_length": {"param": "WaveTrend_avg_len"}}, 
                outputs={"main": "wt_main", "signal": "wt_signal"}
            ),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_period"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_mom_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["high"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["high"].iloc[i-1]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["high"].iloc[i-1]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=4,
            ),
            EntryRuleSpec(
                name="hk50_mom_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["low"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["low"].iloc[i-1]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["low"].iloc[i-1]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=4,
            ),
        ],
    )
