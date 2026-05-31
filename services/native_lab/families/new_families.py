from __future__ import annotations

from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

FamilyRegistry.register(StrategyFamily(
    name="commodities_momentum_breakout",
    mutation_space={
        "params.FastEMA": [9, 13, 21],
        "params.SlowEMA": [34, 55, 89],
        "params.ATRPeriod": [10, 14, 21],
        "params.KeltnerMult": [1.5, 2.0, 2.5],
        "params.StopLossATR": [1.5, 2.5, 3.5],
        "params.ProfitTargetATR": [3.0, 5.0, 8.0],
        "params.ExitAfterBars": [12, 24, 48]
    },
    wfo_param_grid={
        "FastEMA": [9, 13, 21],
        "SlowEMA": [34, 55, 89],
        "KeltnerMult": [1.5, 2.0, 2.5],
        "StopLossATR": [2.0, 3.0],
        "ProfitTargetATR": [4.0, 6.0]
    },
    scoring_profile={
        "profit_factor_weight": 30.0,
        "drawdown_weight": 20.0,
        "wfo_weight": 20.0,
        "trade_count_weight": 10.0,
        "mc_weight": 10.0,
        "stability_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.2,
        "max_drawdown_pct": 25.0,
        "min_trades": 50,
        "min_wfo_robustness": 0.4
    }
))

FamilyRegistry.register(StrategyFamily(
    name="gbpjpy_trend_follower",
    mutation_space={
        "params.EMA1": [20, 50, 100],
        "params.EMA2": [100, 200],
        "params.RSIPeriod": [9, 14, 21],
        "params.RSITrendThreshold": [50, 60],
        "params.ATRStopMult": [1.5, 2.0, 3.0]
    },
    wfo_param_grid={
        "EMA1": [20, 50, 100],
        "RSIPeriod": [9, 14, 21],
        "ATRStopMult": [1.5, 2.0, 3.0]
    },
    scoring_profile={
        "profit_factor_weight": 25.0,
        "drawdown_weight": 25.0,
        "wfo_weight": 20.0,
        "mc_weight": 10.0,
        "trade_count_weight": 10.0,
        "stability_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.15,
        "max_drawdown_pct": 30.0,
        "min_trades": 80,
        "min_wfo_robustness": 0.35
    }
))

FamilyRegistry.register(StrategyFamily(
    name="asian_european_mean_reversion",
    mutation_space={
        "params.BBPeriod": [14, 20, 30],
        "params.BBDev": [2.0, 2.5, 3.0],
        "params.RSIPeriod": [5, 9, 14],
        "params.RSIOverbought": [70, 75, 80],
        "params.RSIOversold": [20, 25, 30],
        "params.StopLossATR": [1.0, 1.5, 2.0],
        "params.ProfitTargetATR": [1.0, 2.0, 3.0],
        "params.SessionStart": ["01:00", "03:00"],
        "params.SessionEnd": ["08:00", "10:00"]
    },
    wfo_param_grid={
        "BBPeriod": [14, 20, 30],
        "RSIPeriod": [5, 9, 14],
        "BBDev": [2.0, 2.5, 3.0],
        "StopLossATR": [1.2, 1.8],
        "ProfitTargetATR": [1.5, 2.5]
    },
    scoring_profile={
        "sharpe_weight": 25.0,
        "profit_factor_weight": 20.0,
        "drawdown_weight": 20.0,
        "trade_count_weight": 15.0,
        "wfo_weight": 10.0,
        "mc_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.1,
        "max_drawdown_pct": 20.0,
        "min_trades": 100,
        "min_wfo_robustness": 0.3
    }
))

FamilyRegistry.register(StrategyFamily(
    name="global_index_open_breakout",
    mutation_space={
        "params.OpenBars": [4, 8, 12],
        "params.ATRPeriod": [10, 14, 20],
        "params.ATRMult": [0.5, 1.0, 1.5],
        "params.StopLossATR": [1.0, 1.5, 2.0],
        "params.ProfitTargetATR": [2.0, 3.0, 4.0],
        "params.SessionStart": ["09:30", "08:00"],
        "params.SessionEnd": ["11:30", "12:00"]
    },
    wfo_param_grid={
        "OpenBars": [4, 8, 12],
        "StopLossATR": [1.0, 1.5, 2.0],
        "ProfitTargetATR": [2.0, 3.0, 4.0]
    },
    scoring_profile={
        "profit_factor_weight": 35.0,
        "drawdown_weight": 25.0,
        "wfo_weight": 15.0,
        "mc_weight": 15.0,
        "trade_count_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.25,
        "max_drawdown_pct": 20.0,
        "min_trades": 60,
        "min_wfo_robustness": 0.4
    }
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_us100_reversion_h1",
    mutation_space={
        "params.BBPeriod1": [21, 34, 55],
        "params.BBDev1": [1.5, 2.0, 2.5, 3.0],
        "params.WPRPeriod1": [13, 21, 34],
        "params.WPRUpper": [-20.0, -15.0, -10.0],
        "params.WPRLower": [-90.0, -85.0, -80.0],
        "params.ATRPeriod1": [10, 14, 21],
        "params.StopLossCoef1": [1.5, 2.5, 3.5, 5.0],
        "params.ProfitTargetCoef1": [1.2, 1.8, 2.4, 3.5],
        "params.SignalTimeRangeFrom": ["00:00", "01:00", "08:00", "13:00"],
        "params.SignalTimeRangeTo": ["20:00", "22:00", "23:59"],
        "params.FridayExitTime": ["21:00", "22:30", "22:55"]
    },
    wfo_param_grid={
        "BBPeriod1": [21, 34, 55],
        "BBDev1": [2.0, 2.5],
        "WPRPeriod1": [13, 21, 34],
        "StopLossCoef1": [2.5, 3.5],
        "ProfitTargetCoef1": [1.8, 2.4]
    },
    scoring_profile={
        "profit_factor_weight": 35.0,
        "drawdown_weight": 25.0,
        "trade_count_weight": 15.0,
        "wfo_weight": 15.0,
        "mc_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.10,
        "max_drawdown_pct": 20.0,
        "min_trades": 60,
        "min_wfo_robustness": 0.35
    }
))

FamilyRegistry.register(StrategyFamily(
    name="session_breakout_extreme",
    mutation_space={
        "params.SessionHighLowPeriod": [15, 20, 24, 34],
        "params.EntryBufferATR": [0.0, 0.1, 0.2, 0.5],
        "params.StopLossATR": [1.0, 2.0, 3.0, 4.0],
        "params.ProfitTargetATR": [2.0, 3.0, 4.0, 6.0],
        "params.BreakoutStart": ["08:00", "09:00", "10:00", "11:00", "14:00"],
        "params.BreakoutEnd": ["11:00", "16:00", "20:00"],
        "params.ExpiryBars": [3, 5, 8, 12, 24],
        "params.ADXFilterLevel": [0, 15, 20, 25],
        "params.TrendSMA": [0, 50, 100, 200]
    },
    wfo_param_grid={
        "SessionHighLowPeriod": [15, 20, 34],
        "StopLossATR": [1.0, 2.0, 3.0],
        "ProfitTargetATR": [2.0, 4.0, 6.0]
    },
    scoring_profile={
        "profit_factor_weight": 30.0,
        "drawdown_weight": 20.0,
        "sharpe_weight": 20.0,
        "trade_count_weight": 10.0,
        "wfo_weight": 10.0,
        "mc_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.18,
        "max_drawdown_pct": 25.0,
        "min_trades": 40,
        "min_wfo_robustness": 0.35
    }
))
