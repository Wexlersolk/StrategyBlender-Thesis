from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_m30_momentum_drive",
    description="Inverted HK50 M30 strategy: Buys extreme strength (RSI > 90), uses Limit Orders, and Volatility Gate.",
    family="hk50_momentum",
    regime="M30 Intraday Momentum Drive",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("M30",),
    preferred_timeframes=("M30",),
    sort_order=87
)
def build_hk50_m30_momentum_drive_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "RSI_period": 2,
        "RSI_buy_threshold": 90, # Buy when extremely overbought (Momentum Drive)
        "RSI_sell_threshold": 10, # Sell when extremely oversold
        "VolGate_ATR_prd": 14,
        "VolGate_WMA_prd": 50,
        "LimitOffsetPips": 5.0, # Place limit order 5 pips below current price for better fill
        "ATR_SL_multiplier": 3.0,
        "ATR_TP_multiplier": 6.0,
        "SignalTimeRangeFrom": "03:20", # Corrected for HK50 open
        "SignalTimeRangeTo": "05:00", # Focused on the first 90 mins
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    # Inverted Logic: Buy when RSI > threshold (Momentum Burst)
    # Volatility Gate: Only trade when ATR(14) > WMA(ATR, 50) - i.e., volatility is expanding
    long_signal = f'(df["rsi"] > {params["RSI_buy_threshold"]}) & (df["atr"] > df["atr_wma"])'
    short_signal = f'(df["rsi"] < {params["RSI_sell_threshold"]}) & (df["atr"] > df["atr_wma"])'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="Inverted HK50 Momentum Drive with VolGate and Limit Orders.",
        indicators=[
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSI_period"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "VolGate_ATR_prd"}}),
            IndicatorSpec("atr_wma", "wma", {"series": "atr", "period": {"param": "VolGate_WMA_prd"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_mom_drive_long",
                side="long",
                order_type="buy_limit",
                when='bool(df["long_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["open"].iloc[i]) - (float(self.p("LimitOffsetPips")) * 0.01)', # Limit below open
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=2,
            ),
            EntryRuleSpec(
                name="hk50_mom_drive_short",
                side="short",
                order_type="sell_limit",
                when='bool(df["short_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["open"].iloc[i]) + (float(self.p("LimitOffsetPips")) * 0.01)', # Limit above open
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=2,
            ),
        ],
    )
