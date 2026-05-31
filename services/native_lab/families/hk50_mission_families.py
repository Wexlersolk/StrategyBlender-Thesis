from __future__ import annotations
from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

# M30 Reversion Family
FamilyRegistry.register(StrategyFamily(
    name="hk50_m30_reversion",
    mutation_space={
        "params.RSI_period": [2, 3, 5, 7, 10],
        "params.RSI_oversold": [10, 15, 20, 25],
        "params.RSI_overbought": [75, 80, 85, 90],
        "params.Laguerre_gamma": [0.5, 0.6, 0.7, 0.8],
        "params.ATR_SL_multiplier": [1.5, 2.0, 2.5, 3.0],
        "params.ATR_TP_multiplier": [2.0, 3.0, 4.0, 5.0, 6.0],
        "params.SignalTimeRangeTo": ["03:00", "04:30", "06:00"],
    },
    wfo_param_grid={
        "RSI_period": [2, 5],
        "Laguerre_gamma": [0.6, 0.8],
        "ATR_SL_multiplier": [2.0, 3.0],
    },
    scoring_profile={
        "profit_factor_weight": 40.0,
        "drawdown_weight": 20.0,
        "trade_count_weight": 15.0,
        "stability_weight": 25.0,
    },
    promotion_policy={
        "min_profit_factor": 1.15,
        "max_drawdown_pct": 15.0,
        "min_trades": 50,
    }
))

# M15 Momentum Family
FamilyRegistry.register(StrategyFamily(
    name="hk50_m15_momentum",
    mutation_space={
        "params.EMA_period": [50, 100, 150, 200],
        "params.WaveTrend_ch_len": [9, 10, 12, 14],
        "params.WaveTrend_avg_len": [14, 21, 28],
        "params.ATR_period": [10, 14, 21],
        "params.ATR_SL_multiplier": [1.5, 2.0, 2.5, 3.0],
        "params.ATR_TP_multiplier": [2.5, 3.5, 4.5, 6.0],
        "params.SignalTimeRangeTo": ["03:00", "04:30", "05:30"],
    },
    wfo_param_grid={
        "EMA_period": [100, 200],
        "WaveTrend_ch_len": [9, 12],
        "ATR_SL_multiplier": [2.0, 3.0],
    },
    scoring_profile={
        "profit_factor_weight": 35.0,
        "drawdown_weight": 25.0,
        "trade_count_weight": 20.0,
        "stability_weight": 20.0,
    },
    promotion_policy={
        "min_profit_factor": 1.12,
        "max_drawdown_pct": 18.0,
        "min_trades": 60,
    }
))

# M30 Momentum Drive Family (Inverted Reversion)
FamilyRegistry.register(StrategyFamily(
    name="hk50_m30_momentum_drive",
    mutation_space={
        "params.RSI_period": [2, 3, 5],
        "params.RSI_buy_threshold": [85, 90, 95],
        "params.RSI_sell_threshold": [5, 10, 15],
        "params.VolGate_WMA_prd": [30, 50, 70],
        "params.LimitOffsetPips": [0.0, 5.0, 10.0, 20.0],
        "params.ATR_SL_multiplier": [2.5, 3.0, 4.0],
        "params.ATR_TP_multiplier": [4.0, 6.0, 8.0],
    },
    wfo_param_grid={
        "RSI_period": [2, 3],
        "VolGate_WMA_prd": [50, 70],
    },
    scoring_profile={
        "profit_factor_weight": 45.0,
        "drawdown_weight": 25.0,
        "trade_count_weight": 10.0,
        "stability_weight": 20.0,
    },
    promotion_policy={
        "min_profit_factor": 1.15,
        "max_drawdown_pct": 15.0,
        "min_trades": 30, # Lower trade count target due to VolGate
    }
))

# H4 High Conviction Family
FamilyRegistry.register(StrategyFamily(
    name="hk50_h4_high_conviction",
    mutation_space={
        "params.ADX_period": [10, 14, 21],
        "params.ADX_threshold": [25, 30, 35, 40],
        "params.ATR_WMA_period": [30, 50, 80],
        "params.LinReg_period": [20, 30, 50],
        "params.ATR_SL_multiplier": [2.5, 3.5, 4.5],
        "params.ATR_TP_multiplier": [5.0, 7.0, 10.0],
    },
    wfo_param_grid={
        "ADX_threshold": [25, 30, 35],
        "LinReg_period": [20, 30, 50],
    },
    scoring_profile={
        "profit_factor_weight": 50.0,
        "drawdown_weight": 20.0,
        "trade_count_weight": 10.0,
        "stability_weight": 20.0,
    },
    promotion_policy={
        "min_profit_factor": 1.20,
        "max_drawdown_pct": 12.0,
        "min_trades": 20, # Targeting very high quality, low frequency
    }
))
