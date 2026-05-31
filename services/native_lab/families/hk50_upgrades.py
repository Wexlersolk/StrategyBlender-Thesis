from __future__ import annotations
from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

FamilyRegistry.register(StrategyFamily(
    name="hk50_breakout_v2",
    mutation_space={
        "entry_archetype": ["breakout_stop", "breakout_close"],
        "long_signal_mode": ["wpr_rising", "qqe_bullish", "momentum_rising", "ema_bias", "ha_reclaim", "wavetrend_bullish", "rsi_rising", "linreg_below", "fractal_cross_hma"],
        "short_signal_mode": ["wpr_falling", "qqe_bearish", "momentum_falling", "laguerre_falling", "ema_bias", "wavetrend_bearish", "rsi_falling", "atr_cross_ma", "fractal_cross_wma"],
        "volatility_filter": ["none", "atr_cross_ma", "bb_squeeze"],
        "trend_filter": ["none", "ema_trend"],
        "params.HighestPeriod": [10, 15, 20, 30, 45, 60],
        "params.LowestPeriod": [10, 15, 20, 30, 45, 60, 100, 150],
        "params.ATRPeriod": [14, 19, 21, 30],
        "params.StopLossATR": [1.5, 2.3, 3.2],
        "params.ProfitTargetATR": [2.0, 3.0, 4.0, 5.5],
        "params.StopLossShortATR": [1.5, 1.8, 2.1, 2.5],
        "params.ProfitTargetShortATR": [2.5, 3.2, 4.4],
        "params.EMAFast": [10, 20, 30],
        "params.EMASlow": [50, 100],
        "params.LinRegPeriod": [14, 20, 28],
        "params.HMAPeriod": [34, 48, 60],
        "params.FractalBars": [3, 5],
    },
    wfo_param_grid={
        "HighestPeriod": [15, 20, 30],
        "ATRPeriod": [14, 21],
        "StopLossATR": [2.3, 3.2],
        "ProfitTargetATR": [4.0, 5.5],
    },
    scoring_profile={
        "profit_factor_weight": 35.0,
        "drawdown_weight": 25.0,
        "trade_count_weight": 10.0,
        "wfo_weight": 15.0,
        "mc_weight": 15.0,
    },
    promotion_policy={
        "min_profit_factor": 1.2,
        "max_drawdown_pct": 20.0,
        "min_trades": 40,
        "min_wfo_robustness": 0.4,
        "min_win_rate": 0.35,
    }
))
