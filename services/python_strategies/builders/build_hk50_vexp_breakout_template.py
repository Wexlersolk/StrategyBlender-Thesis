from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_vexp_breakout",
    description="HK50 Volatility Expansion Breakout. High-conviction entries during ATR spikes.",
    family="hk50_vexp",
    regime="Intraday Volatility Expansion",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("M15", "M30"),
    preferred_timeframes=("M15",),
    sort_order=87
)
def build_hk50_vexp_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "ATR_Period": 14,
        "ATR_MA_Period": 50,
        "VEXP_Threshold": 1.1, 
        "Breakout_Period": 5, 
        "ATR_SL_multiplier": 3.0,
        "ATR_TP_multiplier": 2.0,
        "SignalTimeRangeFrom": "01:15", # UTC
        "SignalTimeRangeTo": "04:30",   # UTC
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    # Logic in UTC time using direct index math
    # 01:15 UTC = 75 mins, 04:30 UTC = 270 mins
    time_filter = '(df.index.hour * 60 + df.index.minute >= 75) & (df.index.hour * 60 + df.index.minute <= 270)'
    
    v_expansion = 'df["atr"] > (df["atr_ma"] * self.p("VEXP_Threshold"))'
    long_signal = f'({v_expansion}) & (df["close"] > df["high"].shift(1)) & {time_filter}'
    short_signal = f'({v_expansion}) & (df["close"] < df["low"].shift(1)) & {time_filter}'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="HK50 Volatility Expansion Breakout.",
        indicators=[
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_Period"}}),
            IndicatorSpec("atr_ma", "sma", {"series": "atr", "period": {"param": "ATR_MA_Period"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_vexp_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1])',
                price='float(df["open"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=1,
            ),
            EntryRuleSpec(
                name="hk50_vexp_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1])',
                price='float(df["open"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=1,
            ),
        ],
    )
