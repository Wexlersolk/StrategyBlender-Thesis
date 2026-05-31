from __future__ import annotations
from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

# Upgraded Discovery Grammar for Gold
FamilyRegistry.register(StrategyFamily(
    name="xau_discovery_grammar",
    mutation_space={
        "direction_mode": ["both", "long_only", "short_only"],
        "entry_archetype": ["breakout_stop", "breakout_close", "pullback_trend", "ema_reclaim", "atr_pullback_limit", "heiken_reclaim", "ichimoku_momentum", "session_reclaim", "range_fade_reclaim", "vwap_pullback", "qqe_momentum"],
        "volatility_filter": ["bb_width", "atr_expansion", "session_impulse", "choppiness_filter", "none"],
        "session_filter": ["london_ny", "london_only", "ny_only", "all_day"],
        "stop_model": ["atr", "channel", "swing", "atr_anchor"],
        "target_model": ["fixed_rr", "atr_scaled", "trend_runner", "asymmetric_runner"],
        "exit_model": ["session_close", "time_exit", "trailing_atr", "break_even_then_trail", "channel_flip", "atr_time_stop", "trailing_swing", "friday_flat", "ema_flip"],
        "params.HighestPeriod": [16, 24, 36, 48],
        "params.LowestPeriod": [16, 24, 36, 48],
        "params.ATRPeriod": [10, 14, 21],
        "params.FastEMA": [9, 13, 21, 34],
        "params.SlowEMA": [34, 55, 89, 144],
        "params.RSIPeriod": [9, 14, 21],
        "params.VWAPPeriod": [10, 20, 50, 100],
        "params.QQERSIPeriod": [9, 14, 21],
        "params.QQESmoothPeriod": [3, 5, 8],
        "params.QQEFactor": [2.618, 4.236, 5.0],
        "params.BBWRPeriod": [18, 24, 36],
        "params.BBWRMin": [0.05, 0.1, 0.15, 0.2],
        "params.ChopThreshold": [45.0, 50.0, 55.0, 60.0],
        "params.StopLossATR": [1.1, 1.4, 1.8, 2.2],
        "params.ProfitTargetATR": [2.0, 2.8, 3.6, 4.5],
        "params.TrailATR": [0.8, 1.1, 1.5],
        "params.PullbackATR": [0.2, 0.4, 0.6, 0.9],
        "params.ExitAfterBars": [12, 18, 24, 36],
    },
    wfo_param_grid={
        "FastEMA": [13, 21, 34],
        "ProfitTargetATR": [2.0, 2.8, 3.6],
        "StopLossATR": [1.1, 1.4, 1.8],
    },
    scoring_profile={
        "profit_factor_weight": 40.0,
        "drawdown_weight": 20.0,
        "wfo_weight": 15.0,
        "sharpe_weight": 15.0,
        "trade_count_weight": 10.0,
    },
    promotion_policy={
        "min_profit_factor": 1.25,
        "max_drawdown_pct": 15.0,
        "min_trades": 80,
        "min_wfo_robustness": 0.45,
        "min_win_rate": 0.40,
    }
))

# New Premium Momentum Family for Gold
FamilyRegistry.register(StrategyFamily(
    name="xau_premium_momentum_v3",
    mutation_space={
        "params.FastEMA": [13, 21, 34],
        "params.SlowEMA": [55, 89, 144],
        "params.ATRPeriod": [14, 21],
        "params.StopLossATR": [1.5, 2.0, 2.5],
        "params.ProfitTargetATR": [3.0, 4.5, 6.0],
        "params.ExitAfterBars": [24, 48, 72],
        "params.ChopThreshold": [50.0, 55.0]
    },
    scoring_profile={
        "profit_factor_weight": 45.0,
        "drawdown_weight": 25.0,
        "sharpe_weight": 20.0,
        "wfo_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.35,
        "max_drawdown_pct": 12.0,
        "min_trades": 60,
        "min_wfo_robustness": 0.5
    }
))

# New Precision Reversion Family for Gold
FamilyRegistry.register(StrategyFamily(
    name="xau_precision_reversion_v3",
    mutation_space={
        "params.BBPeriod": [20, 30, 50],
        "params.BBDev": [2.2, 2.5, 2.8],
        "params.RSIPeriod": [7, 9, 14],
        "params.RSIOverbought": [75, 80, 85],
        "params.RSIOversold": [15, 20, 25],
        "params.StopLossATR": [1.2, 1.5, 1.8],
        "params.ProfitTargetATR": [1.8, 2.2, 2.6]
    },
    scoring_profile={
        "sharpe_weight": 35.0,
        "profit_factor_weight": 30.0,
        "drawdown_weight": 25.0,
        "trade_count_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.3,
        "max_drawdown_pct": 10.0,
        "min_trades": 100,
        "min_wfo_robustness": 0.4
    }
))
