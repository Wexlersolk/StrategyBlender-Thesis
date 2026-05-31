from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required

@register_template(
    name="hk50_m30_reversion",
    description="Specialized HK50 M30 Mean Reversion template focusing on over-extension and session timing.",
    family="hk50_reversion",
    regime="M30 Intraday Mean Reversion",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("M30",),
    preferred_timeframes=("M30",),
    sort_order=85
)
def build_hk50_m30_reversion_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "RSI_period": 2,
        "RSI_oversold": 10,
        "RSI_overbought": 90,
        "Laguerre_gamma": 0.6,
        "Laguerre_oversold": 0.1,
        "Laguerre_overbought": 0.9,
        "ATR_SL_multiplier": 2.5,
        "ATR_TP_multiplier": 4.0,
        "SignalTimeRangeFrom": "01:15",
        "SignalTimeRangeTo": "04:30",
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal = f'(df["rsi"] < {params["RSI_oversold"]}) | (df["laguerre"] < {params["Laguerre_oversold"]})'
    short_signal = f'(df["rsi"] > {params["RSI_overbought"]}) | (df["laguerre"] > {params["Laguerre_overbought"]})'
    
    vfilter = 'pd.Series(True, index=df.index)'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="HK50 M30 Reversion specialized.",
        indicators=[
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSI_period"}}),
            IndicatorSpec("laguerre", "sq_laguerre_rsi", {"close": "close", "gamma": {"param": "Laguerre_gamma"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": 14}),
        ],
        series=[
            SeriesSpec("long_signal", f'({long_signal}) & ({vfilter})'),
            SeriesSpec("short_signal", f'({short_signal}) & ({vfilter})'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_rev_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["open"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) - float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) + float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=5,
            ),
            EntryRuleSpec(
                name="hk50_rev_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["open"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["open"].iloc[i]) + float(self.p("ATR_SL_multiplier")) * float(df["atr"].iloc[i-1])',
                take_profit='float(df["open"].iloc[i]) - float(self.p("ATR_TP_multiplier")) * float(df["atr"].iloc[i-1])',
                expiry_bars=5,
            ),
        ],
    )
