from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_h4_high_conviction",
    description="Extreme H4 HK50 strategy: Uses ADX and ATR expansion to isolate only high-conviction trends.",
    family="hk50_breakout",
    regime="H4 Structural Trend",
    supported_symbols=("HK50.cash", "GBPJPY"),
    supported_timeframes=("H4", "H1"),
    preferred_timeframes=("H4", "H1"),
    sort_order=88
)
def build_hk50_h4_high_conviction_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "ADX_period": 14,
        "ADX_threshold": 30, # High conviction threshold
        "ATR_period": 14,
        "ATR_WMA_period": 50,
        "LinReg_period": 30,
        "ATR_SL_multiplier": 3.5, # Wider stops for H4
        "ATR_TP_multiplier": 7.0, # Target large structural moves
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    # Entry Logic: 
    # 1. ADX > Threshold (Strong Trend)
    # 2. ATR > ATR_WMA (Volatility Expanding)
    # 3. Price > LinReg (Directional Bias)
    long_signal = f'(df["adx"] > {params["ADX_threshold"]}) & (df["atr"] > df["atr_wma"]) & (df["close"] > df["linreg"])'
    short_signal = f'(df["adx"] > {params["ADX_threshold"]}) & (df["atr"] > df["atr_wma"]) & (df["close"] < df["linreg"])'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="HK50 H4 High Conviction Breakout.",
        indicators=[
            IndicatorSpec("adx_res", "sq_adx", {"period": {"param": "ADX_period"}}, outputs={"adx": "adx"}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_period"}}),
            IndicatorSpec("atr_wma", "wma", {"series": "atr", "period": {"param": "ATR_WMA_period"}}),
            IndicatorSpec("linreg", "sq_linreg", {"series": "close", "period": {"param": "LinReg_period"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_h4_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1])',
                price='float(df["high"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["high"].iloc[i-1]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["high"].iloc[i-1]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=4,
            ),
            EntryRuleSpec(
                name="hk50_h4_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1])',
                price='float(df["low"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["low"].iloc[i-1]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["low"].iloc[i-1]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=4,
            ),
        ],
    )
