from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_v_reversion_pro",
    description="High-precision HK50 M15 Mean Reversion focusing on over-extension RECLAIM.",
    family="hk50_reversion",
    regime="Intraday Mean Reversion Reclaim",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("M15", "M30"),
    preferred_timeframes=("M15",),
    sort_order=88
)
def build_hk50_v_reversion_pro_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "BB_Period": 20,
        "BB_Dev": 2.5,
        "RSI_Period": 14,
        "RSI_Floor": 30,
        "RSI_Ceil": 70,
        "ATR_SL_multiplier": 2.0,
        "ATR_TP_multiplier": 2.0, 
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal = '(df["close"].shift(1) < df["bb_lower"].shift(1)) & (df["close"] > df["bb_lower"]) & (df["rsi"] < self.p("RSI_Ceil"))'
    short_signal = '(df["close"].shift(1) > df["bb_upper"].shift(1)) & (df["close"] < df["bb_upper"]) & (df["rsi"] > self.p("RSI_Floor"))'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="HK50 Mean Reversion Reclaim.",
        indicators=[
            # FIX: Use full OHLC for bollinger_bands and rename 'std_dev' to 'deviations'
            IndicatorSpec("bb_res", "bollinger_bands", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "BB_Period"}, "deviations": {"param": "BB_Dev"}}, outputs={"upper": "bb_upper", "lower": "bb_lower"}),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSI_Period"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": 14}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_rev_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1])',
                price='float(df["high"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["high"].iloc[i-1]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["high"].iloc[i-1]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=1,
            ),
            EntryRuleSpec(
                name="hk50_rev_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1])',
                price='float(df["low"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["low"].iloc[i-1]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["low"].iloc[i-1]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=1,
            ),
        ],
    )
