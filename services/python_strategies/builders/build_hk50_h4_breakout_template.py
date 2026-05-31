from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="hk50_h4_breakout",
    description="Optimized HK50 H4 Breakout template based on SQX survivors.",
    family="hk50_breakout",
    regime="H4 Breakout and Momentum",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=80
)
def build_hk50_h4_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "mmLots": 1.0,
        "StopLossCoef1": 2.3,
        "ProfitTargetCoef1": 2.0,
        "StopLossCoef2": 1.5,
        "ProfitTargetCoef2": 4.4,
        "Highest_period": 10,
        "Lowest_period": 100,
        "Highest_mode": 0, 
        "Lowest_mode": 0,  
        "ATR_period": 30,
        "WPR_period": 20,
        "Momentum_period": 80,
        "QQE_rsi_period": 50,
        "QQE_smooth": 5,
        "QQE_factor": 4.236,
        "LinReg_period": 20,
        "Laguerre_gamma": 0.2,
        "WaveTrend_ch_len": 9,
        "WaveTrend_avg_len": 21,
        "Fractal_bars": 5,
        "HMA_period": 48,
        "Stoch_K": 14,
        "Stoch_D": 3,
        "Stoch_Slowing": 3,
        "EMA_filter_period": 20,
        "Volatility_ATR_prd": 20,
        "Volatility_WMA_prd": 58,
        "TrailingStopCoef1": 1.0,
        "TrailingActCef1": 1.5,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
    }
    
    for key, value in defaults.items():
        params.setdefault(key, value)
    
    long_signal_mode = str(payload.get("long_signal_mode", "wpr_rising"))
    short_signal_mode = str(payload.get("short_signal_mode", "wpr_rising"))
    volatility_filter = str(payload.get("volatility_filter", "none"))
    trend_filter = str(payload.get("trend_filter", "none"))
    
    # Long Signal Logic
    if long_signal_mode == "wpr_rising":
        long_signal = '_rising(df["wpr"], 2, 1)'
    elif long_signal_mode == "qqe_bullish":
        long_signal = 'df["qqe"] > df["qqe_signal"]'
    elif long_signal_mode == "momentum_rising":
        long_signal = '_rising(df["momentum"], 2, 1)'
    elif long_signal_mode == "laguerre_falling":
        long_signal = '_falling(df["laguerre"], 2, 1)'
    elif long_signal_mode == "linreg_below":
        long_signal = 'df["open"] < df["linreg"]'
    elif long_signal_mode == "wavetrend_bullish":
        long_signal = 'df["wt_main"] > df["wt_signal"]'
    elif long_signal_mode == "stoch_falling":
        long_signal = '_falling(df["stoch_d"], 2, 1)'
    elif long_signal_mode == "fractal_hma":
        long_signal = '_cross_above(df["fractal_down"], df["hma"])'
    elif long_signal_mode == "hour_morning":
        long_signal = 'df.index.hour < 11'
    else:
        long_signal = 'df["close"] > df["close"].shift(1)'
        
    # Short Signal Logic
    if short_signal_mode == "wpr_rising":
        short_signal = '_rising(df["wpr"], 2, 1)'
    elif short_signal_mode == "qqe_bearish":
        short_signal = 'df["qqe"] < df["qqe_signal"]'
    elif short_signal_mode == "momentum_falling":
        short_signal = '_falling(df["momentum"], 2, 1)'
    elif short_signal_mode == "laguerre_rising":
        short_signal = '_rising(df["laguerre"], 2, 1)'
    elif short_signal_mode == "linreg_above":
        short_signal = 'df["open"] > df["linreg"]'
    elif short_signal_mode == "wavetrend_bearish":
        short_signal = 'df["wt_main"] < df["wt_signal"]'
    elif short_signal_mode == "stoch_falling":
        short_signal = '_falling(df["stoch_d"], 2, 1)'
    elif short_signal_mode == "fractal_hma":
        short_signal = '_cross_above(df["fractal_up"], df["hma"])'
    elif short_signal_mode == "sma_falling":
        short_signal = '_falling(df["sma_20"], 2, 1)'
    else:
        short_signal = 'df["close"] < df["close"].shift(1)'

    # Volatility Filter
    if volatility_filter == "atr_cross_ma":
        vfilter = 'df["vol_atr"] > df["vol_atr_ma"]'
    else:
        vfilter = 'pd.Series(True, index=df.index)'
        
    # Trend Filter
    if trend_filter == "ema_below_close":
        tfilter_long = 'df["ema_f"] < df["close"]'
        tfilter_short = 'df["ema_f"] > df["close"]'
    else:
        tfilter_long = 'pd.Series(True, index=df.index)'
        tfilter_short = 'pd.Series(True, index=df.index)'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=100,
        lot_value=float(payload.get("lot_value", 1.0)),
        description="HK50 H4 Breakout optimized builder from SQX survivors.",
        indicators=[
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPR_period"}}),
            IndicatorSpec("qqe_res", "sq_qqe", {"close": "close", "rsi_period": {"param": "QQE_rsi_period"}, "smooth_period": {"param": "QQE_smooth"}, "factor": {"param": "QQE_factor"}}, outputs={"qqe": "qqe", "lower": "qqe_signal"}),
            IndicatorSpec("momentum", "sq_momentum", {"series": "close", "period": {"param": "Momentum_period"}}),
            IndicatorSpec("laguerre", "sq_laguerre_rsi", {"close": "close", "gamma": {"param": "Laguerre_gamma"}}),
            IndicatorSpec("linreg", "sq_linreg", {"series": "close", "period": {"param": "LinReg_period"}}),
            IndicatorSpec("wt_res", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrend_ch_len"}, "average_length": {"param": "WaveTrend_avg_len"}}, outputs={"main": "wt_main", "signal": "wt_signal"}),
            IndicatorSpec("stoch_res", "sq_stochastic", {"high": "high", "low": "low", "close": "close", "k_period": {"param": "Stoch_K"}, "d_period": {"param": "Stoch_D"}, "slowing": {"param": "Stoch_Slowing"}}, outputs={"main": "stoch_k", "signal": "stoch_d"}),
            IndicatorSpec("ema_f", "ema", {"series": "close", "period": {"param": "EMA_filter_period"}}),
            IndicatorSpec("fractal_res", "sq_fractal", {"high": "high", "low": "low", "bars": {"param": "Fractal_bars"}}, outputs={"up": "fractal_up", "down": "fractal_down"}),
            IndicatorSpec("hma", "sq_hma", {"series": "close", "period": {"param": "HMA_period"}}),
            IndicatorSpec("vol_atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "Volatility_ATR_prd"}}),
            IndicatorSpec("vol_atr_ma", "wma", {"series": "vol_atr", "period": {"param": "Volatility_WMA_prd"}}),
            IndicatorSpec("sma_20", "sma", {"series": "close", "period": 20}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": {"param": "Highest_mode"}}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": {"param": "Lowest_mode"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR_period"}}),
        ],
        series=[
            SeriesSpec("long_signal", f'({long_signal}) & ({vfilter}) & ({tfilter_long})'),
            SeriesSpec("short_signal", f'({short_signal}) & ({vfilter}) & ({tfilter_short})'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i - 1]) - float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i - 1])',
                take_profit='float(df["highest"].iloc[i - 1]) + float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr"].iloc[i - 1])',
                expiry_bars=10,
                comment="hk50_long",
            ),
            EntryRuleSpec(
                name="hk50_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i - 1]) + float(self.p("StopLossCoef2")) * float(df["atr"].iloc[i - 1])',
                take_profit='float(df["lowest"].iloc[i - 1]) - float(self.p("ProfitTargetCoef2")) * float(df["atr"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr"].iloc[i - 1])',
                expiry_bars=10,
                comment="hk50_short",
            ),
        ],
    )
