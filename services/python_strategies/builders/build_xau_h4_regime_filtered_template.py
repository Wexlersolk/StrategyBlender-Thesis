from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="xau_h4_regime_filtered",
    description="Macro Gold H4 with ADX Slope Filter to avoid 2026 choppy markets.",
    family="xau_macro",
    regime="H4 Structural Trend",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=90
)
def build_xau_h4_regime_filtered_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "HighestPeriod": 48,
        "LowestPeriod": 48,
        "EMAPeriod": 200,
        "ADX_period": 14,
        "ADX_threshold": 25,
        "ATR_period": 14,
        "ATR_SL_multiplier": 4.5,
        "ATR_TP_multiplier": 9.0,
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    # Logic: 
    # 1. Price > EMA (Trend)
    # 2. ADX > Threshold (Strength)
    # 3. ADX[0] > ADX[1] (Increasing Momentum - the 'Regime Gate')
    # 4. Breakout of HH(Period)
    
    long_signal = (
        f'(df["close"] > df["ema"]) & '
        f'(df["adx"] > {params["ADX_threshold"]}) & '
        f'(df["adx"] > df["adx"].shift(1)) & '
        f'(df["close"] > df["hh"].shift(1))'
    )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=400,
        lot_value=1.0,
        description="XAU H4 Regime Filtered (ADX Slope).",
        indicators=[
            IndicatorSpec("ema", "sq_ema", {"series": "close", "period": {"param": "EMAPeriod"}}),
            IndicatorSpec("adx_res", "sq_adx", {"period": {"param": "ADX_period"}}, outputs={"adx": "adx"}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_period"}}),
            IndicatorSpec("hh", "sq_highest", {"series": "high", "period": {"param": "HighestPeriod"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="xau_regime_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1])',
                price='float(df["hh"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["hh"].iloc[i-1]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["hh"].iloc[i-1]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=4,
            ),
        ],
    )
