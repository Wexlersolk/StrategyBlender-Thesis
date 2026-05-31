from __future__ import annotations

from services.native_lab.family_registry import StrategyFamily, FamilyRegistry

FamilyRegistry.register(StrategyFamily(
    name="breakout_confirm",
    mutation_space={'params.HighestPeriod': [15, 20, 34], 'params.LowestPeriod': [15, 20, 34], 'params.ATRPeriod': [10, 14, 21], 'params.BBWRPeriod': [14, 20, 28], 'params.MaxDistancePct': [2.5, 4.0, 6.0], 'params.StopLossATR': [1.2, 1.8, 2.5, 3.2], 'params.ProfitTargetATR': [1.5, 2.5, 4.0, 6.0], 'direction': ['long', 'short'], 'expiry_bars': [2, 3, 5]},
    wfo_param_grid={'HighestPeriod': [15, 20, 34], 'LowestPeriod': [15, 20, 34], 'ATRPeriod': [10, 14, 21], 'BBWRPeriod': [14, 20, 28], 'MaxDistancePct': [2.5, 4.0, 6.0], 'StopLossATR': [1.8, 2.5], 'ProfitTargetATR': [2.5, 4.0]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.15, 'max_drawdown_pct': 25.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.52, 'min_score': 52.0}
))

FamilyRegistry.register(StrategyFamily(
    name="reversion",
    mutation_space={'params.BBPeriod': [14, 20, 26], 'params.BBMult': [1.8, 2.0, 2.4], 'params.WPRPeriod': [10, 14, 21], 'params.ATRPeriod': [10, 14, 21], 'params.StopLossATR': [1.2, 1.8, 2.5], 'params.ProfitTargetATR': [1.2, 2.0, 3.5], 'params.WPROversold': [-90.0, -80.0, -70.0], 'params.WPROverbought': [-30.0, -20.0, -10.0]},
    wfo_param_grid={'BBPeriod': [14, 20, 26], 'WPRPeriod': [10, 14, 21], 'ATRPeriod': [10, 14, 21], 'WPROversold': [-90.0, -80.0, -70.0], 'WPROverbought': [-30.0, -20.0, -10.0], 'StopLossATR': [1.5, 2.0], 'ProfitTargetATR': [1.5, 2.0]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 18.0, 'drawdown_weight': 24.0, 'trade_count_weight': 12.0, 'wfo_weight': 10.0, 'mc_weight': 6.0, 'stability_weight': 8.0},
    promotion_policy={'min_trades': 12, 'min_profit_factor': 1.08, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.32, 'min_mc_prob_profit': 0.48, 'min_score': 48.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_batch",
    mutation_space={'long_signal_mode': ['cross_above', 'rising', 'simple_above'], 'short_signal_mode': ['cross_below', 'falling', 'simple_below'], 'params.IndicatorCrsMAPrd1': [21, 34, 55, 89, 144], 'params.IndicatorCrsMAPrd2': [21, 34, 55, 89, 144], 'params.Highest_period': [12, 24, 48, 72, 96, 120, 240], 'params.Lowest_period': [12, 24, 48, 72, 96, 120, 240], 'params.ATR1_period': [10, 14, 20, 28], 'params.ATR2_period': [10, 14, 20, 28], 'params.ATR3_period': [10, 14, 20, 28], 'params.ATR4_period': [50, 75, 100, 150, 200], 'params.StopLossCoef1': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'params.ProfitTargetCoef1': [2.5, 3.5, 4.5, 5.5, 6.5, 8.0], 'params.StopLossCoef2': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0], 'params.ProfitTargetCoef2': [2.5, 3.5, 4.5, 5.5, 6.5, 8.0], 'params.TrailingActCef1': [1.0, 1.5, 2.0, 2.5, 3.0], 'params.TrailingStop1': [50.0, 100.0, 150.0, 200.0, 300.0], 'params.SignalTimeRangeFrom': ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00'], 'params.SignalTimeRangeTo': ['14:00', '16:00', '18:00', '20:00', '22:00', '23:59']},
    wfo_param_grid={},
    scoring_profile={'sharpe_weight': 25.0, 'profit_factor_weight': 15.0, 'drawdown_weight': 15.0, 'trade_count_weight': 10.0, 'wfo_weight': 10.0, 'mc_weight': 5.0, 'stability_weight': 10.0, 'equity_stability_weight': 10.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.15, 'max_drawdown_pct': 25.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.5, 'min_score': 55.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_fx_h4_swing_reversion",
    mutation_space={'params.BBPeriod': [14, 20, 26], 'params.BBMult': [1.8, 2.0, 2.4], 'params.WPRPeriod': [10, 14, 21], 'params.ATRPeriod': [10, 14, 21], 'params.StopLossATR': [1.5, 2.0, 2.5], 'params.ProfitTargetATR': [2.5, 3.5, 4.5]},
    wfo_param_grid={'BBPeriod': [14, 20, 26], 'BBMult': [1.8, 2.0, 2.4], 'WPRPeriod': [10, 14, 21]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 24.0, 'trade_count_weight': 10.0, 'wfo_weight': 12.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.12, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 52.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_gold_h4_ichi_momentum",
    mutation_space={'params.IchimokuTenkan': [7, 9, 12], 'params.IchimokuKijun': [22, 26, 30], 'params.IchimokuSenkou': [44, 52, 60], 'params.RSIPeriod': [10, 14, 21], 'params.RSIThreshold': [50, 55, 60], 'params.StopLossATR': [1.5, 2.2, 3.0], 'params.ProfitTargetATR': [3.0, 5.0, 7.5]},
    wfo_param_grid={'IchimokuTenkan': [7, 9, 12], 'IchimokuKijun': [22, 26, 30], 'RSIPeriod': [10, 14, 21], 'RSIThreshold': [50, 55, 60]},
    scoring_profile={'sharpe_weight': 26.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 20.0, 'trade_count_weight': 6.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 15, 'min_profit_factor': 1.2, 'max_drawdown_pct': 15.0, 'min_wfo_robustness': 0.45, 'min_mc_prob_profit': 0.58, 'min_score': 60.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_after_retest_h4",
    mutation_space={'trend_bias_mode': ['sar_bias', 'ichimoku_bias', 'adx_bias'], 'entry_style': ['stop', 'market_reclaim'], 'params.DIPeriod1': [10, 14, 21], 'params.SARStep': [0.18, 0.266, 0.34], 'params.SARMax': [0.5, 0.69, 0.9], 'params.ATRPeriod1': [14, 20, 28], 'params.PriceEntryMult1': [0.2, 0.3, 0.5], 'params.StopLossATR': [1.5, 2.0, 2.6], 'params.ProfitTargetATR': [2.2, 3.0, 3.8], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20'], 'params.SignalTimeRangeTo': ['00:20', '00:26', '00:35']},
    wfo_param_grid={'DIPeriod1': [10, 14, 21], 'SARStep': [0.18, 0.266, 0.34], 'PriceEntryMult1': [0.2, 0.3, 0.5]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 18.0, 'trade_count_weight': 6.0, 'wfo_weight': 18.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 6, 'min_profit_factor': 1.18, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.54, 'min_score': 55.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_batch_h1",
    mutation_space={'long_signal_mode': ['ao_cross', 'range_break', 'opening_drive'], 'short_signal_mode': ['lwma_cross', 'range_break', 'opening_reversal'], 'params.LWMAPeriod1': [8, 10, 14, 21, 28], 'params.IndicatorCrsMAPrd1': [28, 34, 47, 60, 75], 'params.StopLossCoef1': [1.4, 1.8, 2.5, 3.2, 3.8], 'params.ProfitTargetCoef1': [1.8, 2.2, 2.8, 3.6, 4.4], 'params.TrailingActCef1': [0.8, 1.0, 1.4, 1.8, 2.2], 'params.TrailingStop1': [70.0, 95.0, 127.5, 160.0, 220.0], 'params.StopLossCoef2': [1.8, 2.2, 3.0, 3.8, 4.4], 'params.ProfitTargetCoef2': [1.4, 1.8, 2.2, 2.8, 3.4], 'params.TrailingStopCoef1': [0.6, 0.8, 1.0, 1.3, 1.6], 'params.ATR1_period': [10, 14, 19, 24, 30], 'params.ATR2_period': [28, 34, 45, 55, 70], 'params.ATR3_period': [8, 10, 14, 18, 22], 'params.ATR4_period': [55, 70, 100, 130, 160], 'params.Highest_period': [20, 34, 50, 70, 90], 'params.Lowest_period': [20, 34, 50, 70, 90], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:26', '02:15', '04:30'], 'params.SignalTimeRangeTo': ['01:30', '03:00', '05:00', '08:30', '11:00', '14:00']},
    wfo_param_grid={'LWMAPeriod1': [10, 14, 21], 'IndicatorCrsMAPrd1': [34, 47, 60], 'Highest_period': [34, 50, 70], 'Lowest_period': [34, 50, 70]},
    scoring_profile={'sharpe_weight': 20.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 18.0, 'trade_count_weight': 10.0, 'wfo_weight': 16.0, 'mc_weight': 8.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 25, 'min_profit_factor': 1.1, 'max_drawdown_pct': 28.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_before_retest_h4",
    mutation_space={'signal_mode': ['rsi_reversal', 'fibo_reclaim', 'sma_fade'], 'entry_style': ['stop', 'market_reclaim'], 'params.RSIPeriod1': [10, 14, 21], 'params.Period1': [34, 50, 70], 'params.SMAPeriod1': [14, 20, 28], 'params.ATRPeriod1': [34, 50, 70], 'params.ATRPeriod2': [14, 19, 24], 'params.ATRPeriod3': [50, 65, 80], 'params.PriceEntryMult1': [0.2, 0.3, 0.5], 'params.ProfitTargetCoef1': [2.2, 3.0, 3.8], 'params.TrailingActCef1': [1.0, 1.4, 1.8], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20'], 'params.SignalTimeRangeTo': ['00:20', '00:26', '00:35']},
    wfo_param_grid={'RSIPeriod1': [10, 14, 21], 'Period1': [34, 50, 70], 'PriceEntryMult1': [0.2, 0.3, 0.5]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 18.0, 'trade_count_weight': 6.0, 'wfo_weight': 18.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 6, 'min_profit_factor': 1.15, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 53.0}
))

FamilyRegistry.register(StrategyFamily(
    name="hk50_h4_breakout",
    mutation_space={
        'long_signal_mode': ['wpr_rising', 'qqe_bullish', 'momentum_rising', 'hour_morning', 'linreg_below', 'wavetrend_bullish', 'fractal_hma'],
        'short_signal_mode': ['wpr_rising', 'qqe_bearish', 'momentum_falling', 'sma_falling', 'linreg_above', 'wavetrend_bearish', 'stoch_falling'],
        'volatility_filter': ['none', 'atr_cross_ma'],
        'trend_filter': ['none', 'ema_below_close'],
        'params.Highest_period': [10, 14, 20, 34],
        'params.Lowest_period': [10, 14, 20, 34, 100],
        'params.ATR_period': [14, 20, 28, 34],
        'params.StopLossCoef1': [1.5, 1.8, 2.2, 2.6, 3.2],
        'params.ProfitTargetCoef1': [2.8, 3.2, 4.0, 5.5, 7.5],
        'params.StopLossCoef2': [1.5, 1.8, 2.2, 2.6, 3.2],
        'params.ProfitTargetCoef2': [2.8, 3.2, 4.0, 5.5, 7.5],
        'params.TrailingActCef1': [1.0, 1.5, 2.0],
        'params.TrailingStopCoef1': [0.5, 1.0, 1.5]
    },
    wfo_param_grid={'Highest_period': [10, 14, 20], 'ATR_period': [14, 20]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 10.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 35, 'min_profit_factor': 1.12, 'max_drawdown_pct': 28.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.50, 'min_score': 32.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_ichi_heiken_h1",
    mutation_space={'params.IchimokuTenkanPrd1': [7, 9, 12], 'params.IchimokuKijunPeriod1': [22, 26, 30], 'params.IchimokuSenkouPrd1': [38, 52, 65], 'params.IndicatorMAPeriod1': [60, 72, 84], 'params.Highest_period': [40, 50, 60, 72], 'params.Lowest_period': [40, 50, 60, 72], 'params.ATRFastPeriod': [10, 14, 19], 'params.ATRSlowPeriod': [14, 19, 24], 'params.EntryBufferATR': [0.08, 0.12, 0.18], 'params.StopLossCoef1': [1.4, 1.6, 1.9, 2.2], 'params.ProfitTargetCoef1': [3.8, 4.8, 5.9], 'params.StopLossCoef2': [2.0, 2.6, 3.1], 'params.ProfitTargetCoef2': [2.0, 2.4, 3.0], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20', '00:35', '00:45', '02:15', '03:30'], 'params.SignalTimeRangeTo': ['00:26', '00:35', '00:45', '01:00', '01:30', '05:00', '08:30']},
    wfo_param_grid={'IchimokuTenkanPrd1': [7, 9, 12], 'IchimokuKijunPeriod1': [22, 26, 30], 'Highest_period': [40, 50, 60], 'Lowest_period': [40, 50, 60], 'EntryBufferATR': [0.08, 0.12, 0.18]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 20.0, 'drawdown_weight': 26.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 10.0, 'mt5_corr_weight': 10.0, 'drawdown_scale': 12.0},
    promotion_policy={'min_trades': 7, 'min_profit_factor': 1.12, 'max_drawdown_pct': 20.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0, 'min_mt5_correlation_score': 0.5}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_ichimoku_channel_h1",
    mutation_space={'params.IchimokuTenkanPrd1': [7, 9, 12], 'params.IchimokuKijunPeriod1': [22, 26, 30], 'params.IchimokuSenkouPrd1': [38, 52, 65], 'params.Highest_period': [40, 50, 60, 72], 'params.Lowest_period': [40, 50, 60, 72], 'params.ATRFastPeriod': [10, 14, 19], 'params.ATRSlowPeriod': [14, 19, 24], 'params.EntryBufferATR': [0.0, 0.06, 0.12], 'params.StopLossCoef1': [1.4, 1.6, 1.9, 2.2], 'params.ProfitTargetCoef1': [4.2, 5.2, 5.9], 'params.StopLossCoef2': [2.2, 2.6, 3.1], 'params.ProfitTargetCoef2': [2.0, 2.4, 3.0], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20', '00:35', '00:45', '02:15', '03:30'], 'params.SignalTimeRangeTo': ['00:26', '00:35', '00:45', '01:00', '01:30', '05:00', '08:30']},
    wfo_param_grid={'IchimokuTenkanPrd1': [7, 9, 12], 'IchimokuKijunPeriod1': [22, 26, 30], 'Highest_period': [40, 50, 60], 'Lowest_period': [40, 50, 60], 'EntryBufferATR': [0.0, 0.06, 0.12]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 20.0, 'drawdown_weight': 24.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 10.0, 'mt5_corr_weight': 10.0, 'drawdown_scale': 12.0},
    promotion_policy={'min_trades': 7, 'min_profit_factor': 1.12, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0, 'min_mt5_correlation_score': 0.5}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_pivot_kama_wavetrend_h1",
    mutation_space={'params.KAMAERPeriod1': [56, 72, 100, 120], 'params.KAMAShortPeriod1': [21, 34, 56], 'params.KAMALongPeriod1': [21, 27, 34], 'params.WaveTrendChannelLng1': [21, 34, 53, 72], 'params.WaveTrendAverageLng1': [14, 21, 28], 'params.WaveTrendSignalLng1': [3, 4, 6], 'params.PivotStartMinute': [5, 13, 20, 26, 35], 'params.Highest_period': [50, 70, 90, 110], 'params.Lowest_period': [40, 60, 80], 'params.ATRFastPeriod': [10, 14, 19], 'params.ATRSlowPeriod': [14, 19, 24], 'params.ATRTrailPeriod': [55, 70, 100, 130], 'params.StopLossCoef1': [1.4, 1.6, 1.9, 2.2], 'params.ProfitTargetCoef1': [1.8, 2.2, 2.8], 'params.TrailingStopCoef1': [0.8, 1.0, 1.2, 1.5], 'params.StopLossCoef2': [2.2, 2.7, 3.1], 'params.ProfitTargetCoef2': [1.8, 2.2, 2.8], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20', '00:35', '00:45', '02:15', '03:30'], 'params.SignalTimeRangeTo': ['00:26', '00:35', '00:45', '01:00', '01:30', '05:00', '08:30']},
    wfo_param_grid={'KAMAERPeriod1': [56, 72, 100], 'WaveTrendChannelLng1': [21, 34, 53], 'PivotStartMinute': [13, 20, 26], 'Highest_period': [50, 70, 90], 'Lowest_period': [40, 60, 80]},
    scoring_profile={'sharpe_weight': 20.0, 'profit_factor_weight': 20.0, 'drawdown_weight': 26.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 10.0, 'mt5_corr_weight': 10.0, 'drawdown_scale': 12.0},
    promotion_policy={'min_trades': 7, 'min_profit_factor': 1.12, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0, 'min_mt5_correlation_score': 0.5}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_hk50_wavetrend_break_h1",
    mutation_space={'params.WaveTrendChannelLng1': [10, 14, 18, 21], 'params.WaveTrendAverageLng1': [14, 21, 28], 'params.EMAPeriod1': [30, 40, 50, 60], 'params.Highest_period': [25, 35, 45], 'params.Lowest_period': [25, 35, 45], 'params.ATRFastPeriod': [10, 14, 19], 'params.ATRSlowPeriod': [14, 19, 24], 'params.StopLossCoef1': [1.7, 2.1, 2.6], 'params.ProfitTargetCoef1': [4.2, 5.2, 6.0], 'params.StopLossCoef2': [1.8, 2.2, 2.7], 'params.ProfitTargetCoef2': [2.4, 3.0, 3.6], 'params.TrailingStop1': [120.0, 155.0, 190.0], 'params.SignalTimeRangeFrom': ['00:05', '00:13', '00:20', '00:35', '00:45', '02:15', '03:30'], 'params.SignalTimeRangeTo': ['00:26', '00:35', '00:45', '01:00', '01:30', '05:00', '08:30']},
    wfo_param_grid={'WaveTrendChannelLng1': [10, 14, 18], 'WaveTrendAverageLng1': [14, 21, 28], 'EMAPeriod1': [30, 40, 50], 'Highest_period': [25, 35, 45], 'Lowest_period': [25, 35, 45]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 20.0, 'drawdown_weight': 24.0, 'trade_count_weight': 10.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 10.0, 'mt5_corr_weight': 10.0, 'drawdown_scale': 12.0},
    promotion_policy={'min_trades': 7, 'min_profit_factor': 1.12, 'max_drawdown_pct': 20.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0, 'min_mt5_correlation_score': 0.5}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_index_h4_trend_reclaim",
    mutation_space={'params.FastEMA': [13, 21, 34], 'params.SlowEMA': [89, 144, 200], 'params.ATRPeriod': [10, 14, 21], 'params.PullbackATR': [0.5, 1.0, 1.5], 'params.StopLossATR': [2.0, 3.0, 4.0], 'params.ProfitTargetATR': [4.0, 6.0, 8.0]},
    wfo_param_grid={'FastEMA': [13, 21, 34], 'SlowEMA': [89, 144, 200], 'PullbackATR': [0.5, 1.0, 1.5]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 20.0, 'drawdown_weight': 24.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 12, 'min_profit_factor': 1.15, 'max_drawdown_pct': 18.0, 'min_wfo_robustness': 0.42, 'min_mc_prob_profit': 0.55, 'min_score': 55.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_uk100_ulcer_keltner_h1",
    mutation_space={'params.UlcerPeriod': [34, 48, 64], 'params.KCPeriod': [14, 20, 28], 'params.KCMult1': [1.75, 2.25, 2.75], 'params.EntryOffsetCoef1': [1.8, 2.3, 3.0], 'params.StopLossCoef1': [1.2, 1.5, 2.0], 'params.ProfitTargetCoef1': [2.5, 3.5, 5.0], 'params.StopLossCoef2': [1.5, 2.0, 2.5], 'params.ProfitTargetCoef2': [2.4, 3.4, 4.5], 'params.TrailingActCoef1': [1.0, 1.2, 1.5], 'params.ATR1_period': [34, 50, 75], 'params.ATR2_period': [14, 19, 26], 'params.ATR3_period': [75, 100, 130], 'params.ATR4_period': [10, 14, 21], 'params.SignalTimeRangeFrom': ['00:00', '00:13', '08:00'], 'params.SignalTimeRangeTo': ['00:26', '12:00', '16:00']},
    wfo_param_grid={'UlcerPeriod': [34, 48, 64], 'KCPeriod': [14, 20, 28], 'KCMult1': [1.75, 2.25, 2.75]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.14, 'max_drawdown_pct': 23.0, 'min_wfo_robustness': 0.36, 'min_mc_prob_profit': 0.5, 'min_score': 51.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_us100_nasdaq_ichi_keltner",
    mutation_space={'params.SMMAPeriod1': [24, 30, 40, 50, 60], 'params.IchimokuTenkanPrd1': [6, 7, 9, 12, 15], 'params.IchimokuKijunPeriod1': [18, 22, 26, 30, 36], 'params.IchimokuSenkouPrd1': [16, 26, 38, 52, 65], 'params.KeltnerChannelPrd1': [40, 55, 70, 85, 100], 'params.KeltnerMult1': [1.8, 2.0, 2.25, 2.5, 2.8], 'params.LowestPeriod1': [16, 20, 25, 30, 36], 'params.PriceEntryMult1': [0.8, 1.2, 1.6, 2.0, 2.4], 'params.PriceEntryMult2': [0.5, 0.8, 1.2, 1.6, 2.0], 'params.ProfitTargetCoef1': [3.2, 4.0, 5.0, 6.0, 7.0], 'params.StopLossCoef1': [1.2, 1.5, 1.9, 2.3, 2.8], 'params.ProfitTargetCoef2': [2.2, 2.8, 3.6, 4.4, 5.2], 'params.StopLossCoef2': [1.0, 1.2, 1.5, 1.8, 2.2], 'params.ATRPeriod1': [10, 14, 21, 34], 'params.ATRPeriod2': [10, 14, 21, 34], 'params.ATRPeriod3': [10, 14, 21, 34], 'params.ATRPeriod4': [10, 14, 21, 34], 'params.SignalTimeRangeFrom': ['00:00', '00:05', '00:15', '08:00', '13:00'], 'params.SignalTimeRangeTo': ['12:00', '16:00', '20:00', '22:30', '23:00', '23:59'], 'params.FridayExitTime': ['22:00', '22:15', '22:38', '22:50']},
    wfo_param_grid={},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.15, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 53.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_us100_nasdaq_qqe",
    mutation_space={'params.QQERsiPeriod1': [8, 10, 14, 18, 22], 'params.QQESmooth1': [2, 3, 5, 7, 9], 'params.QQERsiPeriod2': [42, 55, 69, 84, 100], 'params.QQESmooth2': [2, 3, 5, 7, 9], 'params.SMAEntryPeriod1': [21, 34, 53, 72, 89], 'params.SessionLowLookback': [8, 10, 14, 20, 28], 'params.PriceEntryMult1': [0.4, 0.8, 1.2, 1.6, 2.0], 'params.PriceEntryMult2': [0.3, 0.6, 0.9, 1.2, 1.5], 'params.ExitAfterBars1': [8, 12, 18, 24, 30], 'params.ExitAfterBars2': [8, 12, 19, 26, 32], 'params.ProfitTargetCoef1': [2.8, 3.4, 4.2, 5.0, 6.0], 'params.StopLossCoef1': [1.2, 1.5, 1.9, 2.3, 2.8], 'params.ProfitTargetCoef2': [2.4, 3.0, 3.7, 4.4, 5.2], 'params.StopLossCoef2': [1.1, 1.4, 1.7, 2.0, 2.4], 'params.ATRPeriod1': [14, 24, 40, 50], 'params.ATRPeriod2': [14, 19, 29, 40], 'params.ATRPeriod3': [10, 14, 21, 34], 'params.ATRPeriod4': [10, 14, 21, 34], 'params.TrailingStopCoef1': [0.6, 0.8, 1.0, 1.2, 1.5], 'params.TrailingStop1': [60.0, 80.0, 105.0, 130.0, 160.0], 'params.TrailingActivation1': [20.0, 30.0, 45.0, 60.0, 75.0], 'params.SignalTimeRangeFrom': ['00:00', '00:05', '00:15', '08:00', '13:00'], 'params.SignalTimeRangeTo': ['12:00', '16:00', '20:00', '22:30', '23:00', '23:59'], 'params.FridayExitTime': ['22:00', '22:15', '22:38', '22:50']},
    wfo_param_grid={},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.15, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 53.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_us100_nasdaq_smma_keltner",
    mutation_space={'params.SMMAPeriod1': [8, 10, 12, 16, 20], 'params.EWMAPeriod1': [16, 18, 20, 24, 28], 'params.ROCPeriod1': [8, 10, 12, 16, 20], 'params.ROCThreshold1': [48.5, 49.5, 50.3, 51.0, 52.0], 'params.KCFastPeriod1': [12, 16, 20, 24, 28], 'params.KCFastMult1': [2.0, 2.2, 2.5, 2.8, 3.1], 'params.KCSlowPeriod1': [48, 55, 73, 89, 110], 'params.KCSlowMult1': [1.8, 2.0, 2.4, 2.8, 3.2], 'params.PriceEntryMult1': [1.0, 1.5, 2.0, 2.5, 3.0], 'params.ExitAfterBars1': [6, 8, 12, 16, 20], 'params.ProfitTargetCoef1': [4.0, 4.8, 6.0, 7.2, 8.5], 'params.StopLossCoef1': [1.4, 1.8, 2.2, 2.6, 3.0], 'params.ProfitTargetCoef2': [3.4, 4.2, 5.6, 6.8, 8.0], 'params.StopLossCoef2': [1.4, 1.8, 2.3, 2.8, 3.2], 'params.ATRPeriod1': [14, 24, 40, 50], 'params.ATRPeriod2': [14, 19, 29, 40], 'params.ATRPeriod3': [10, 14, 21, 34], 'params.ATRPeriod4': [10, 14, 21, 34], 'params.TrailingStop1': [180.0, 240.0, 360.0, 480.0, 600.0], 'params.TrailingActCef1': [2.0, 2.8, 3.9, 5.0, 6.0], 'params.SignalTimeRangeFrom': ['00:00', '00:05', '00:15', '08:00', '13:00'], 'params.SignalTimeRangeTo': ['12:00', '16:00', '20:00', '22:30', '23:00', '23:59'], 'params.FridayExitTime': ['22:00', '22:15', '22:38', '22:50']},
    wfo_param_grid={},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.16, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 53.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_us30_wpr_stoch",
    mutation_space={'params.StochK': [9, 14, 21], 'params.StochD': [3, 5, 7], 'params.StochSlow': [3, 5, 7], 'params.WPRPeriod': [50, 75, 100], 'params.MaxDistancePct': [4.0, 6.0, 8.0], 'params.HighestPeriod': [15, 20, 34], 'params.LowestPeriod': [15, 20, 34], 'params.ATRPeriod1': [10, 14, 21], 'params.ATRPeriod2': [10, 14, 21], 'params.StopLossCoef1': [1.5, 2.0, 2.5], 'params.ProfitTargetCoef1': [2.0, 3.0, 4.5], 'params.StopLossCoef2': [1.5, 2.0, 2.5], 'params.ProfitTargetCoef2': [2.0, 3.0, 4.5], 'params.SignalTimeRangeFrom': ['00:00', '08:00', '14:00'], 'params.SignalTimeRangeTo': ['16:00', '21:00', '23:59']},
    wfo_param_grid={'StochK': [9, 14, 21], 'StochD': [3, 5, 7], 'StochSlow': [3, 5, 7], 'WPRPeriod': [50, 75, 100], 'MaxDistancePct': [4.0, 6.0, 8.0]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.18, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 54.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_usdjpy_dual_ema_rsi",
    mutation_space={'params.FastEMA': [13, 21, 34], 'params.SlowEMA': [34, 55, 89], 'params.RSIPeriod': [10, 14, 21], 'params.RSIThreshold': [50, 55, 60], 'params.StopLossATR': [1.2, 1.8, 2.4], 'params.ProfitTargetATR': [2.4, 3.6, 4.8], 'params.ATRPeriod': [10, 14, 21], 'params.SignalTimeRangeFrom': ['00:00', '02:00', '08:00'], 'params.SignalTimeRangeTo': ['12:00', '18:00', '23:59']},
    wfo_param_grid={'FastEMA': [13, 21, 34], 'SlowEMA': [34, 55, 89], 'RSIPeriod': [10, 14, 21], 'RSIThreshold': [50, 55, 60]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 22.0, 'trade_count_weight': 10.0, 'wfo_weight': 12.0, 'mc_weight': 6.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.18, 'max_drawdown_pct': 20.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.54, 'min_score': 54.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_usdjpy_ichi_keltner",
    mutation_space={'params.IchimokuTenkan': [7, 9, 12], 'params.IchimokuKijun': [22, 26, 30], 'params.IchimokuSenkou': [44, 52, 60], 'params.KeltnerPeriod': [14, 20, 26], 'params.KeltnerMult': [1.5, 2.0, 2.5], 'params.StopLossATR': [1.5, 2.0, 2.5], 'params.ProfitTargetATR': [3.0, 4.0, 5.0], 'params.ATRPeriod': [10, 14, 21], 'params.SignalTimeRangeFrom': ['00:00', '02:00', '08:00'], 'params.SignalTimeRangeTo': ['12:00', '18:00', '23:59']},
    wfo_param_grid={'IchimokuTenkan': [7, 9, 12], 'IchimokuKijun': [22, 26, 30], 'KeltnerPeriod': [14, 20, 26], 'KeltnerMult': [1.5, 2.0, 2.5]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 18.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 2.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.15, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.52, 'min_score': 52.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_usdjpy_vwap_wt",
    mutation_space={'params.HighestPeriod': [12, 20, 34], 'params.ExitAfterBars1': [8, 14, 21], 'params.EMAPeriod1': [13, 20, 34], 'params.VWAPPeriod1': [55, 77, 120], 'params.PriceEntryMult1': [0.2, 0.3, 0.5], 'params.WaveTrendChannel': [7, 9, 12], 'params.WaveTrendAverage': [45, 60, 80], 'params.IndicatorCrsMAPrd1': [25, 35, 50], 'params.ProfitTargetCoef1': [2.0, 3.0, 4.5], 'params.StopLossCoef1': [1.8, 2.8, 3.8], 'params.ATRPeriod1': [14, 19, 26], 'params.ATRPeriod2': [10, 14, 21]},
    wfo_param_grid={'HighestPeriod': [12, 20, 34], 'ExitAfterBars1': [8, 14, 21], 'EMAPeriod1': [13, 20, 34], 'VWAPPeriod1': [55, 77, 120], 'PriceEntryMult1': [0.2, 0.3, 0.5]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 18.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 7, 'min_profit_factor': 1.16, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.53, 'min_score': 55.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_xau_ao_hour_breakout",
    mutation_space={'direction_mode': ['both', 'long_only', 'short_only'], 'params.LWMAPeriod1': [34, 40, 48], 'params.IndicatorMAPeriod1': [55, 67, 79], 'params.AOPercentile': [42.0, 48.9, 55.0], 'params.AOPercentileLookback': [600, 829, 1000], 'params.AskPercentile': [30.0, 37.3, 45.0], 'params.AskPercentileLookback': [600, 841, 1000], 'params.HighestPeriod': [160, 200, 240], 'params.LowestPeriod': [160, 200, 240], 'params.ATRPeriod': [14, 19, 26], 'params.StopLossCoef1': [1.8, 2.2, 2.6], 'params.ProfitTargetCoef1': [4.0, 5.0, 6.0], 'params.TrailingStop1': [120.0, 155.0, 190.0], 'params.StopLossCoef2': [1.4, 1.8, 2.2], 'params.ProfitTargetCoef2': [2.4, 3.0, 3.8], 'params.LongExpiryBars': [12, 20, 28], 'params.ShortExpiryBars': [10, 14, 18]},
    wfo_param_grid={'LWMAPeriod1': [34, 40, 48], 'IndicatorMAPeriod1': [55, 67, 79], 'HighestPeriod': [160, 200, 240], 'LowestPeriod': [160, 200, 240], 'ATRPeriod': [14, 19, 26], 'StopLossCoef1': [1.8, 2.2, 2.6], 'ProfitTargetCoef1': [4.0, 5.0, 6.0], 'TrailingStop1': [120.0, 155.0, 190.0], 'StopLossCoef2': [1.4, 1.8, 2.2], 'ProfitTargetCoef2': [2.4, 3.0, 3.8]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 22.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 2.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.14, 'max_drawdown_pct': 22.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.52, 'min_score': 54.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_xau_highest_breakout",
    mutation_space={'direction_mode': ['both', 'long_only', 'short_only'], 'long_signal_mode': ['sma_bias', 'smma_pullback', 'ha_reclaim'], 'short_signal_mode': ['lwma_lowest_count', 'wt_push', 'lwma_hour_quantile'], 'params.HighestPeriod': [205, 210, 245], 'params.LowestPeriod': [205, 210, 245], 'params.LongStopATR': [1.5, 1.7, 2.0], 'params.LongTargetATR': [3.4, 3.5, 5.7], 'params.ShortStopATR': [1.5, 1.8, 1.9], 'params.ShortTargetATR': [1.6, 1.9, 4.8], 'params.LongExpiryBars': [2, 4, 10], 'params.ShortExpiryBars': [10, 18], 'params.LongTrailATR': [0.0, 1.0, 2.4], 'params.MaxDistancePct': [4.0, 6.0, 8.0]},
    wfo_param_grid={'HighestPeriod': [205, 210, 245], 'LowestPeriod': [205, 210, 245], 'LongStopATR': [1.5, 1.7, 2.0], 'LongTargetATR': [3.4, 3.5, 5.7], 'ShortStopATR': [1.5, 1.8, 1.9], 'ShortTargetATR': [1.6, 1.9, 4.8], 'LongExpiryBars': [2, 4, 10], 'ShortExpiryBars': [10, 18], 'LongTrailATR': [0.0, 1.0, 2.4]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 4.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.14, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.5, 'min_score': 53.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_xau_osma_bb",
    mutation_space={'params.BBPeriod': [14, 20, 26], 'params.OsmaFast': [5, 8, 13], 'params.OsmaSlow': [13, 17, 26], 'params.ATRPeriod2': [34, 55, 89]},
    wfo_param_grid={'BBPeriod': [120, 167, 220], 'OsmaFast': [5, 8, 13], 'OsmaSlow': [13, 17, 26], 'ATRPeriod2': [34, 55, 89]},
    scoring_profile={'sharpe_weight': 24.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 18.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 9, 'min_profit_factor': 1.14, 'max_drawdown_pct': 26.0, 'min_wfo_robustness': 0.36, 'min_mc_prob_profit': 0.5, 'min_score': 52.0}
))

FamilyRegistry.register(StrategyFamily(
    name="sqx_xau_short_keltner_breakout",
    mutation_space={'direction_mode': ['short_only'], 'short_keltner_band': ['middle', 'upper', 'lower'], 'params.IndicatorMAPeriod1': [47, 59, 71], 'params.StochasticKPeriod1': [10, 14, 18], 'params.StochasticDPeriod1': [5, 7, 9], 'params.StochasticSlowing1': [3, 5, 7], 'params.KCerPeriod1': [14, 20, 26], 'params.HighestPeriod': [300, 370, 440], 'params.LowestPeriod': [300, 370, 440], 'params.ATRTargetPeriod1': [14, 19, 26], 'params.ATRStopPeriod1': [10, 14, 21], 'params.ATRTargetPeriod2': [10, 14, 21], 'params.ATRStopPeriod2': [10, 14, 21], 'params.ProfitTargetCoef1': [2.8, 3.5, 4.2], 'params.StopLossCoef1': [1.6, 2.0, 2.4], 'params.ProfitTargetCoef2': [2.4, 3.1, 3.8], 'params.StopLossCoef2': [2.0, 2.4, 2.8], 'params.LongExpiryBars': [10, 18, 26], 'params.ShortExpiryBars': [1, 2, 3], 'params.FridayExitTime': ['21:45', '22:38', '23:15']},
    wfo_param_grid={'IndicatorMAPeriod1': [47, 59, 71], 'KCerPeriod1': [14, 20, 26], 'LowestPeriod': [300, 370, 440], 'ATRTargetPeriod2': [10, 14, 21], 'ATRStopPeriod2': [10, 14, 21], 'ProfitTargetCoef2': [2.4, 3.1, 3.8], 'StopLossCoef2': [2.0, 2.4, 2.8], 'ShortExpiryBars': [1, 2, 3]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 24.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 2.0},
    promotion_policy={'min_trades': 8, 'min_profit_factor': 1.14, 'max_drawdown_pct': 20.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.52, 'min_score': 54.0}
))

FamilyRegistry.register(StrategyFamily(
    name="trend_pullback",
    mutation_space={'direction': ['long', 'short'], 'params.FastEMA': [13, 21, 34], 'params.SlowEMA': [34, 55, 89], 'params.ATRPeriod': [10, 14, 21], 'params.StopLossATR': [1.5, 2.2, 3.5], 'params.ProfitTargetATR': [2.5, 4.0, 6.5], 'params.WaveTrendChannel': [7, 9, 12], 'params.WaveTrendAverage': [14, 21, 28], 'params.H4TrendFilter': [True, False], 'params.H4TrendEMA': [34, 55, 89], 'params.ExitAfterBars': [8, 12, 16]},
    wfo_param_grid={'FastEMA': [13, 21, 34], 'SlowEMA': [34, 55, 89], 'ATRPeriod': [10, 14, 21], 'StopLossATR': [2.0, 3.0], 'ProfitTargetATR': [3.0, 5.0]},
    scoring_profile={'sharpe_weight': 28.0, 'profit_factor_weight': 18.0, 'drawdown_weight': 18.0, 'trade_count_weight': 10.0, 'wfo_weight': 14.0, 'mc_weight': 6.0, 'stability_weight': 6.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.1, 'max_drawdown_pct': 28.0, 'min_wfo_robustness': 0.35, 'min_mc_prob_profit': 0.5, 'min_score': 50.0}
))

FamilyRegistry.register(StrategyFamily(
    name="xau_breakout_session",
    mutation_space={'direction_mode': ['both', 'long_only', 'short_only'], 'params.HighestPeriod': [16, 24, 36], 'params.LowestPeriod': [16, 24, 36], 'params.ATRPeriod': [10, 14, 21], 'params.StopLossATR': [1.2, 1.6, 2.2], 'params.ProfitTargetATR': [2.2, 3.5, 5.5], 'params.BBWRPeriod': [18, 24, 36], 'params.BBWRMin': [0.05, 0.1, 0.2], 'params.EntryBufferATR': [0.1, 0.15, 0.25], 'params.MaxDistancePct': [2.5, 3.5, 5.0], 'params.ExitAfterBars': [12, 18, 24]},
    wfo_param_grid={'HighestPeriod': [16, 24, 36], 'LowestPeriod': [16, 24, 36], 'ATRPeriod': [10, 14, 21], 'StopLossATR': [1.4, 1.8], 'ProfitTargetATR': [2.8, 4.2], 'BBWRPeriod': [18, 24, 36], 'BBWRMin': [0.01, 0.015, 0.025], 'EntryBufferATR': [0.1, 0.15, 0.25], 'MaxDistancePct': [2.5, 3.5, 5.0], 'ExitAfterBars': [12, 18, 24]},
    scoring_profile={'sharpe_weight': 22.0, 'profit_factor_weight': 24.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 14.0, 'mc_weight': 8.0, 'stability_weight': 4.0, 'novelty_weight': 8.0, 'mt5_corr_weight': 10.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.16, 'max_drawdown_pct': 24.0, 'min_wfo_robustness': 0.4, 'min_mc_prob_profit': 0.53, 'min_score': 55.0, 'min_mt5_correlation_score': 0.58}
))

FamilyRegistry.register(StrategyFamily(
    name="xau_discovery_grammar",
    mutation_space={'direction_mode': ['both', 'long_only', 'short_only'], 'entry_archetype': ['breakout_stop', 'breakout_close', 'pullback_trend', 'ema_reclaim', 'atr_pullback_limit', 'session_reclaim', 'range_fade_reclaim'], 'volatility_filter': ['bb_width', 'atr_expansion', 'session_impulse', 'none'], 'session_filter': ['london_ny', 'london_only', 'ny_only', 'all_day'], 'stop_model': ['atr', 'channel', 'swing', 'atr_anchor'], 'target_model': ['fixed_rr', 'atr_scaled', 'trend_runner', 'asymmetric_runner'], 'exit_model': ['session_close', 'time_exit', 'trailing_atr', 'break_even_then_trail', 'channel_flip', 'atr_time_stop', 'friday_flat', 'ema_flip'], 'params.HighestPeriod': [16, 24, 36], 'params.LowestPeriod': [16, 24, 36], 'params.ATRPeriod': [10, 14, 21], 'params.FastEMA': [13, 21, 34], 'params.SlowEMA': [34, 55, 89], 'params.RSIPeriod': [10, 14, 21], 'params.ReclaimATR': [0.2, 0.4, 0.6], 'params.BBWRPeriod': [18, 24, 36], 'params.BBWRMin': [0.05, 0.1, 0.2], 'params.EntryBufferATR': [0.1, 0.15, 0.25], 'params.StopLossATR': [1.1, 1.4, 1.8], 'params.ProfitTargetATR': [2.0, 2.8, 3.6], 'params.TrailATR': [0.8, 1.1, 1.5], 'params.PullbackLookback': [3, 5, 8], 'params.PullbackATR': [0.4, 0.6, 0.9], 'params.BreakEvenATR': [0.6, 0.8, 1.1], 'params.TimeStopATR': [0.3, 0.4, 0.6], 'params.ExitAfterBars': [12, 18, 24], 'params.MaxDistancePct': [2.5, 3.5, 5.0]},
    wfo_param_grid={'FastEMA': [13, 21, 34], 'ProfitTargetATR': [2.0, 2.8, 3.6], 'PullbackLookback': [3, 5, 8], 'BreakEvenATR': [0.6, 0.8, 1.1], 'ExitAfterBars': [12, 18, 24]},
    scoring_profile={'sharpe_weight': 20.0, 'profit_factor_weight': 22.0, 'drawdown_weight': 20.0, 'trade_count_weight': 8.0, 'wfo_weight': 16.0, 'mc_weight': 8.0, 'stability_weight': 6.0, 'novelty_weight': 10.0, 'mt5_corr_weight': 12.0},
    promotion_policy={'min_trades': 10, 'min_profit_factor': 1.12, 'max_drawdown_pct': 25.0, 'min_wfo_robustness': 0.38, 'min_mc_prob_profit': 0.5, 'min_score': 52.0, 'min_mt5_correlation_score': 0.58}
))
