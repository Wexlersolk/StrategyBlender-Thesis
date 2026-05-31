from __future__ import annotations
from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

FamilyRegistry.register(StrategyFamily(
    name="index_lab",
    mutation_space={
        "params.HighestPeriod": [12, 24, 48, 60, 80, 100, 120],
        "params.StopLossATR": [2.5, 3.5, 4.5, 6.0],
        "params.ProfitTargetATR": [5.0, 10.0, 15.0, 25.0],
        "params.ATRPeriod": [14, 20, 24],
        "params.SlowEMA": [100, 200, 300],
        "params.VolGateCoef": [0.0, 0.8, 1.2],
        "params.UseSqueeze": [0, 1],
        "params.ADXMin": [0.0, 20.0, 25.0],
    },
    wfo_param_grid={
        "HighestPeriod": [24, 48, 60],
        "StopLossATR": [3.0, 4.5, 6.0],
        "ProfitTargetATR": [10.0, 15.0, 20.0],
    },
    scoring_profile={
        "profit_factor_weight": 40.0,
        "drawdown_weight": 20.0,
        "wfo_weight": 15.0,
        "trade_count_weight": 15.0,
        "mc_weight": 10.0
    },
    promotion_policy={
        "min_profit_factor": 1.15,
        "max_drawdown_pct": 35.0,
        "min_trades": 60,
        "min_wfo_robustness": 0.25,
        "min_score": 30.0
    }
))
