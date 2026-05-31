from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="hk50_h4_v2",
    description="Improved HK50 H4 Breakout template with advanced signal modes and archetypes.",
    family="hk50_breakout_v2",
    regime="H4 Breakout and Momentum",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=81
)
def build_hk50_h4_v2_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "StopLossATR": 2.3,
        "ProfitTargetATR": 4.0,
        "StopLossShortATR": 1.8,
        "ProfitTargetShortATR": 3.2,
        "HighestPeriod": 20,
        "LowestPeriod": 20,
        "ATRPeriod": 14,
        "WPRPeriod": 20,
        "MomentumPeriod": 80,
        "QQERSIPeriod": 14,
        "QQESmoothPeriod": 5,
        "QQEFactor": 4.236,
        "LinRegPeriod": 20,
        "LaguerreGamma": 0.8,
        "HMAPeriod": 48,
        "FractalBars": 3,
        "WaveTrendChLen": 9,
        "WaveTrendAvgLen": 21,
        "EMAFast": 20,
        "EMASlow": 50,
        "EMATrend": 200,
        "RSIPeriod": 14,
        "BBPeriod": 20,
        "BBMult": 2.0,
        "VolatilityATRPrd": 20,
        "VolatilityWMAPrd": 58,
        "TrailingStopATR": 1.0,
        "TrailingActivationATR": 1.5,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
        "MaxDistancePct": 5.0,
        "EntryBufferATR": 0.1,
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal_mode = str(payload.get("long_signal_mode", "ema_bias"))
    short_signal_mode = str(payload.get("short_signal_mode", "laguerre_falling"))
    volatility_filter = str(payload.get("volatility_filter", "none"))
    trend_filter = str(payload.get("trend_filter", "none"))
    entry_archetype = str(payload.get("entry_archetype", "breakout_stop"))
    
    # Long Signal Logic
    long_signal_map = {
        "wpr_rising": '_rising(df["wpr"], 2, 1)',
        "qqe_bullish": 'df["qqe"] > df["qqe_signal"]',
        "momentum_rising": '_rising(df["momentum"], 2, 1)',
        "ema_bias": 'df["ema_fast"] > df["ema_slow"]',
        "ha_reclaim": 'df["ha_close"] > df["ha_open"]',
        "wavetrend_bullish": 'df["wt_main"] > df["wt_signal"]',
        "rsi_rising": '_rising(df["rsi"], 2, 1)',
        "linreg_below": 'df["open"].shift(1) < df["linreg"].shift(2)',
        "fractal_cross_hma": '_cross_above(df["fractal_down"].shift(1), df["hma"].shift(1))',
    }
    long_signal = long_signal_map.get(long_signal_mode, long_signal_map["ema_bias"])
        
    # Short Signal Logic
    short_signal_map = {
        "wpr_falling": '_falling(df["wpr"], 2, 1)',
        "qqe_bearish": 'df["qqe"] < df["qqe_signal"]',
        "momentum_falling": '_falling(df["momentum"], 2, 1)',
        "laguerre_falling": '_falling(df["laguerre"], 2, 1)',
        "ema_bias": 'df["ema_fast"] < df["ema_slow"]',
        "wavetrend_bearish": 'df["wt_main"] < df["wt_signal"]',
        "rsi_falling": '_falling(df["rsi"], 2, 1)',
        "atr_cross_ma": '_cross_above(df["vol_atr"].shift(1), df["vol_atr_ma"].shift(1))',
        "fractal_cross_wma": '_cross_above(df["fractal_up"].shift(1), df["vol_atr_ma"].shift(1))',
    }
    short_signal = short_signal_map.get(short_signal_mode, short_signal_map["laguerre_falling"])

    # Volatility Filter
    if volatility_filter == "atr_cross_ma":
        vfilter = 'df["vol_atr"] > df["vol_atr_ma"]'
    elif volatility_filter == "bb_squeeze":
        vfilter = 'df["bb_width"] < df["bb_width"].rolling(100).mean()'
    else:
        vfilter = 'pd.Series(True, index=df.index)'
        
    # Trend Filter
    if trend_filter == "ema_trend":
        tfilter_long = 'df["close"] > df["ema_trend"]'
        tfilter_short = 'df["close"] < df["ema_trend"]'
    else:
        tfilter_long = 'pd.Series(True, index=df.index)'
        tfilter_short = 'pd.Series(True, index=df.index)'

    # Entry Price and Type
    if entry_archetype == "breakout_stop":
        long_order_type = "buy_stop"
        short_order_type = "sell_stop"
        long_price = 'float(df["highest"].iloc[i - 1]) + float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i - 1])'
        short_price = 'float(df["lowest"].iloc[i - 1]) - float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i - 1])'
    else: # breakout_close
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None

    long_entry_base = "ctx.open" if long_order_type == "market" else f"({long_price})"
    short_entry_base = "ctx.open" if short_order_type == "market" else f"({short_price})"

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=200,
        lot_value=float(payload.get("lot_value", 0.1285)),
        description="Improved HK50 H4 Breakout V2 template with expanded signals.",
        indicators=[
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPRPeriod"}}),
            IndicatorSpec("qqe_res", "sq_qqe", {"close": "close", "rsi_period": {"param": "QQERSIPeriod"}, "smooth_period": {"param": "QQESmoothPeriod"}, "factor": {"param": "QQEFactor"}}, outputs={"qqe": "qqe", "lower": "qqe_signal"}),
            IndicatorSpec("momentum", "sq_momentum", {"series": "close", "period": {"param": "MomentumPeriod"}}),
            IndicatorSpec("laguerre", "sq_laguerre_rsi", {"close": "close", "gamma": {"param": "LaguerreGamma"}}),
            IndicatorSpec("wt_res", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrendChLen"}, "average_length": {"param": "WaveTrendAvgLen"}}, outputs={"main": "wt_main", "signal": "wt_signal"}),
            IndicatorSpec("ema_fast", "ema", {"series": "close", "period": {"param": "EMAFast"}}),
            IndicatorSpec("ema_slow", "ema", {"series": "close", "period": {"param": "EMASlow"}}),
            IndicatorSpec("ema_trend", "ema", {"series": "close", "period": {"param": "EMATrend"}}),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSIPeriod"}}),
            IndicatorSpec("bb", "bollinger_bands", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "BBPeriod"}, "deviations": {"param": "BBMult"}}, outputs={"upper": "bb_upper", "lower": "bb_lower"}),
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "close": "ha_close"}),
            IndicatorSpec("hma", "sq_hma", {"series": "close", "period": {"param": "HMAPeriod"}}),
            IndicatorSpec("linreg", "sq_linreg", {"series": "close", "period": {"param": "LinRegPeriod"}}),
            IndicatorSpec("fractal_res", "sq_fractal", {"high": "high", "low": "low", "bars": {"param": "FractalBars"}}, outputs={"up": "fractal_up", "down": "fractal_down"}),
            IndicatorSpec("vol_atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "VolatilityATRPrd"}}),
            IndicatorSpec("vol_atr_ma", "wma", {"series": "vol_atr", "period": {"param": "VolatilityWMAPrd"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 0}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
        ],
        series=[
            SeriesSpec("bb_width", 'df["bb_upper"] - df["bb_lower"]'),
            SeriesSpec("long_signal", f'({long_signal}) & ({vfilter}) & ({tfilter_long})'),
            SeriesSpec("short_signal", f'({short_signal}) & ({vfilter}) & ({tfilter_short})'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_long",
                side="long",
                order_type=long_order_type,
                when='bool(df["long_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price=long_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{long_entry_base} - float(self.p("StopLossATR")) * float(df["atr"].iloc[i - 1])',
                take_profit=f'{long_entry_base} + float(self.p("ProfitTargetATR")) * float(df["atr"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopATR")) * float(df["atr"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActivationATR")) * float(df["atr"].iloc[i - 1])',
                expiry_bars=10,
                comment="hk50_v2_long",
            ),
            EntryRuleSpec(
                name="hk50_short",
                side="short",
                order_type=short_order_type,
                when='bool(df["short_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price=short_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{short_entry_base} + float(self.p("StopLossShortATR")) * float(df["atr"].iloc[i - 1])',
                take_profit=f'{short_entry_base} - float(self.p("ProfitTargetShortATR")) * float(df["atr"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopATR")) * float(df["atr"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActivationATR")) * float(df["atr"].iloc[i - 1])',
                expiry_bars=10,
                comment="hk50_v2_short",
            ),
        ],
    )
