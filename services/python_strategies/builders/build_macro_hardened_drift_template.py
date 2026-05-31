from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="macro_hardened_drift",
    description="Universal Macro Drift template with Regime Gates and News Blackout logic.",
    family="macro",
    regime="Regime-Aware Trend",
    sort_order=80
)
def build_macro_hardened_drift_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    
    params = dict(payload.get("params", {}))
    
    # Defaults for Discovery
    defaults = {
        "mmLots": 1.0,
        "HighestPeriod": 20,
        "LowestPeriod": 20,
        "EMAPeriod": 200,
        "ADX_period": 14,
        "ADX_threshold": 20,
        "ATR_short": 5,
        "ATR_long": 50,
        "Vol_Threshold": 1.5, # Regime Filter: ATR_short / ATR_long < 1.5 (avoid toxic vol)
        "News_Proxy_Mult": 3.0, # News Blackout: ATR(1) / ATR(20) > 3.0
        "ATR_SL_mult": 3.0,
        "ATR_TP_mult": 6.0,
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    # Indicators
    indicators = [
        IndicatorSpec("ema", "sq_ema", {"series": "close", "period": {"param": "EMAPeriod"}}),
        IndicatorSpec("adx", "sq_adx", {"period": {"param": "ADX_period"}}, outputs={"adx": "adx"}),
        IndicatorSpec("atr_s", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_short"}}),
        IndicatorSpec("atr_l", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_long"}}),
        IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": 1}),
        IndicatorSpec("atr_n", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": 20}), # For News Proxy
        IndicatorSpec("hh", "sq_highest", {"series": "high", "period": {"param": "HighestPeriod"}}),
        IndicatorSpec("ll", "sq_lowest", {"series": "low", "period": {"param": "LowestPeriod"}}),
    ]
    
    # Series / Filters
    # 1. Regime Gate: Volatility is stable (not exploding) and ADX is rising/strong
    vol_gate = '(df["atr_s"] / df["atr_l"] <= float(self.p("Vol_Threshold")))'
    adx_gate = f'(df["adx"] > {params["ADX_threshold"]})'
    
    # 2. News Blackout Proxy: ATR(1) spike check
    news_gate = f'(df["atr_1"] / df["atr_n"].shift(1) < {params["News_Proxy_Mult"]})'
    
    # 3. Signals
    long_signal = (
        f'(df["close"] > df["ema"]) & '
        f'(df["close"] > df["hh"].shift(1)) & '
        f'{vol_gate} & {adx_gate} & {news_gate}'
    )
    
    short_signal = (
        f'(df["close"] < df["ema"]) & '
        f'(df["close"] < df["ll"].shift(1)) & '
        f'{vol_gate} & {adx_gate} & {news_gate}'
    )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=400,
        lot_value=1.0,
        description="Macro Drift with Regime Gates (ATR Ratio) and News Proxy (ATR Spike).",
        indicators=indicators,
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        entries=[
            EntryRuleSpec(
                name="macro_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i-1])',
                price='float(df["hh"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["hh"].iloc[i-1]) - float(self.p("ATR_SL_mult")) * float(df["atr_s"].iloc[i-1])',
                take_profit='float(df["hh"].iloc[i-1]) + float(self.p("ATR_TP_mult")) * float(df["atr_s"].iloc[i-1])',
                expiry_bars=4,
            ),
            EntryRuleSpec(
                name="macro_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i-1])',
                price='float(df["ll"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["ll"].iloc[i-1]) + float(self.p("ATR_SL_mult")) * float(df["atr_s"].iloc[i-1])',
                take_profit='float(df["ll"].iloc[i-1]) - float(self.p("ATR_TP_mult")) * float(df["atr_s"].iloc[i-1])',
                expiry_bars=4,
            ),
        ],
    )
