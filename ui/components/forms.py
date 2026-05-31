from __future__ import annotations

import copy
import streamlit as st
from config import settings
from ui.components.common import TIMEFRAMES

def execution_settings_form(prefix: str) -> dict:
    """Renders standard execution settings (commission, spread, slippage)."""
    c1, c2, c3 = st.columns(3)
    with c1:
        commission_per_lot = st.number_input(
            "Commission / lot",
            value=float(settings.DEFAULT_COMMISSION_PER_LOT),
            step=0.1,
            key=f"{prefix}_commission",
        )
    with c2:
        spread_pips = st.number_input(
            "Spread",
            value=float(settings.DEFAULT_SPREAD_PIPS),
            step=0.1,
            key=f"{prefix}_spread",
        )
    with c3:
        slippage_pips = st.number_input(
            "Slippage",
            value=float(settings.DEFAULT_SLIPPAGE_PIPS),
            step=0.1,
            key=f"{prefix}_slippage",
        )
    return {
        "commission_per_lot": float(commission_per_lot),
        "spread_pips": float(spread_pips),
        "slippage_pips": float(slippage_pips),
    }

def benchmark_settings_form(prefix: str) -> dict:
    """Renders standard benchmark overlay settings."""
    c1, c2, c3, c4, c5 = st.columns(5)
    settings_dict = {}
    with c1:
        settings_dict["target_vol"] = st.number_input("Target vol", min_value=0.01, max_value=1.0, value=0.20, step=0.01, key=f"{prefix}_target_vol")
    with c2:
        settings_dict["min_multiplier"] = st.number_input("Min mult", min_value=0.1, max_value=2.0, value=0.50, step=0.05, key=f"{prefix}_min_mult")
    with c3:
        settings_dict["max_multiplier"] = st.number_input("Max mult", min_value=0.2, max_value=3.0, value=1.50, step=0.05, key=f"{prefix}_max_mult")
    with c4:
        settings_dict["soft_dd"] = st.number_input("Soft DD %", min_value=0.1, max_value=50.0, value=5.0, step=0.1, key=f"{prefix}_soft_dd")
    with c5:
        settings_dict["hard_dd"] = st.number_input("Hard DD %", min_value=0.2, max_value=80.0, value=10.0, step=0.1, key=f"{prefix}_hard_dd")
    settings_dict["soft_multiplier"] = st.slider(
        "Soft DD multiplier",
        min_value=0.10,
        max_value=1.00,
        value=0.50,
        step=0.05,
        key=f"{prefix}_soft_dd_mult",
    )
    return settings_dict

def template_param_inputs(template_name: str, params: dict) -> dict:
    """Renders parameter inputs based on strategy template."""
    params = copy.deepcopy(params)

    if template_name == "trend_pullback":
        c1, c2, c3 = st.columns(3)
        params["FastEMA"] = int(c1.number_input("Fast EMA", min_value=1, value=int(params.get("FastEMA", 21)), step=1))
        params["SlowEMA"] = int(c2.number_input("Slow EMA", min_value=2, value=int(params.get("SlowEMA", 55)), step=1))
        params["ATRPeriod"] = int(c3.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod", 14)), step=1))
        c4, c5, c6 = st.columns(3)
        params["WaveTrendChannel"] = int(c4.number_input("WaveTrend Channel", min_value=1, value=int(params.get("WaveTrendChannel", 9)), step=1))
        params["WaveTrendAverage"] = int(c5.number_input("WaveTrend Average", min_value=1, value=int(params.get("WaveTrendAverage", 21)), step=1))
        params["ExitAfterBars"] = int(c6.number_input("Exit After Bars", min_value=0, value=int(params.get("ExitAfterBars", 12)), step=1))
    elif template_name == "breakout_confirm":
        c1, c2, c3 = st.columns(3)
        params["HighestPeriod"] = int(c1.number_input("Highest Period", min_value=1, value=int(params.get("HighestPeriod", 20)), step=1))
        params["LowestPeriod"] = int(c2.number_input("Lowest Period", min_value=1, value=int(params.get("LowestPeriod", 20)), step=1))
        params["ATRPeriod"] = int(c3.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod", 14)), step=1))
        c4, c5 = st.columns(2)
        params["BBWRPeriod"] = int(c4.number_input("BB Width Period", min_value=1, value=int(params.get("BBWRPeriod", 20)), step=1))
        params["BBWRMin"] = float(c5.number_input("BB Width Min", value=float(params.get("BBWRMin", 0.0)), step=0.1))
        params["MaxDistancePct"] = float(st.number_input("Max Distance %", min_value=0.0, value=float(params.get("MaxDistancePct", 4.0)), step=0.1))
    elif template_name == "sqx_us30_wpr_stoch":
        c1, c2, c3 = st.columns(3)
        params["WPRPeriod"] = int(c1.number_input("WPR Period", min_value=1, value=int(params.get("WPRPeriod", 75)), step=1))
        params["StochK"] = int(c2.number_input("Stoch K", min_value=1, value=int(params.get("StochK", 14)), step=1))
        params["StochD"] = int(c3.number_input("Stoch D", min_value=1, value=int(params.get("StochD", 3)), step=1))
        c4, c5, c6 = st.columns(3)
        params["StochSlow"] = int(c4.number_input("Stoch Slow", min_value=1, value=int(params.get("StochSlow", 3)), step=1))
        params["HighestPeriod"] = int(c5.number_input("Highest Period", min_value=1, value=int(params.get("HighestPeriod", 105)), step=1))
        params["LowestPeriod"] = int(c6.number_input("Lowest Period", min_value=1, value=int(params.get("LowestPeriod", 105)), step=1))
        c7, c8, c9 = st.columns(3)
        params["ATRPeriod1"] = int(c7.number_input("ATR 1", min_value=1, value=int(params.get("ATRPeriod1", 14)), step=1))
        params["ATRPeriod2"] = int(c8.number_input("ATR 2", min_value=1, value=int(params.get("ATRPeriod2", 29)), step=1))
        params["MaxDistancePct"] = float(c9.number_input("Max Distance %", min_value=0.0, value=float(params.get("MaxDistancePct", 6.0)), step=0.1))
        t1, t2 = st.columns(2)
        params["SignalTimeRangeFrom"] = t1.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:00")))
        params["SignalTimeRangeTo"] = t2.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "23:59")))
    elif template_name == "sqx_xau_osma_bb":
        c1, c2, c3 = st.columns(3)
        params["StochK"] = int(c1.number_input("Stoch K", min_value=1, value=int(params.get("StochK", 21)), step=1))
        params["StochD"] = int(c2.number_input("Stoch D", min_value=1, value=int(params.get("StochD", 7)), step=1))
        params["StochSlow"] = int(c3.number_input("Stoch Slow", min_value=1, value=int(params.get("StochSlow", 7)), step=1))
        c4, c5, c6 = st.columns(3)
        params["OsmaFast"] = int(c4.number_input("OsMA Fast", min_value=1, value=int(params.get("OsmaFast", 8)), step=1))
        params["OsmaSlow"] = int(c5.number_input("OsMA Slow", min_value=1, value=int(params.get("OsmaSlow", 17)), step=1))
        params["OsmaSignal"] = int(c6.number_input("OsMA Signal", min_value=1, value=int(params.get("OsmaSignal", 9)), step=1))
        c7, c8, c9 = st.columns(3)
        params["BBPeriod"] = int(c7.number_input("BB Period", min_value=1, value=int(params.get("BBPeriod", 167)), step=1))
        params["BBDev"] = float(c8.number_input("BB Dev", min_value=0.1, value=float(params.get("BBDev", 1.8)), step=0.1))
        params["ATRPeriod1"] = int(c9.number_input("ATR 1", min_value=1, value=int(params.get("ATRPeriod1", 200)), step=1))
        t1, t2, t3 = st.columns(3)
        params["ATRPeriod2"] = int(t1.number_input("ATR 2", min_value=1, value=int(params.get("ATRPeriod2", 55)), step=1))
        params["SignalTimeRangeFrom"] = t2.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:00")))
        params["SignalTimeRangeTo"] = t3.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "23:59")))
    elif template_name == "xau_breakout_session":
        c1, c2, c3 = st.columns(3)
        params["HighestPeriod"] = int(c1.number_input("Highest Period", min_value=1, value=int(params.get("HighestPeriod", 24)), step=1))
        params["LowestPeriod"] = int(c2.number_input("Lowest Period", min_value=1, value=int(params.get("LowestPeriod", 24)), step=1))
        params["ATRPeriod"] = int(c3.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod", 14)), step=1))
        c4, c5, c6 = st.columns(3)
        params["BBWRPeriod"] = int(c4.number_input("BB Width Period", min_value=1, value=int(params.get("BBWRPeriod", 24)), step=1))
        params["BBWRMin"] = float(c5.number_input("BB Width Min", min_value=0.0, value=float(params.get("BBWRMin", 0.015)), step=0.001, format="%.3f"))
        params["EntryBufferATR"] = float(c6.number_input("Entry Buffer ATR", min_value=0.0, value=float(params.get("EntryBufferATR", 0.15)), step=0.05))
        c7, c8, c9 = st.columns(3)
        params["MaxDistancePct"] = float(c7.number_input("Max Distance %", min_value=0.0, value=float(params.get("MaxDistancePct", 3.5)), step=0.1))
        params["ExitAfterBars"] = int(c8.number_input("Exit After Bars", min_value=0, value=int(params.get("ExitAfterBars", 18)), step=1))
        params["SignalTimeRangeFrom"] = c9.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "06:00")))
        params["SignalTimeRangeTo"] = st.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "18:00")))
    elif template_name == "xau_discovery_grammar":
        c1, c2, c3 = st.columns(3)
        params["HighestPeriod"] = int(c1.number_input("Highest Period", min_value=1, value=int(params.get("HighestPeriod", 24)), step=1))
        params["LowestPeriod"] = int(c2.number_input("Lowest Period", min_value=1, value=int(params.get("LowestPeriod", 24)), step=1))
        params["ATRPeriod"] = int(c3.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod", 14)), step=1))
        c4, c5, c6 = st.columns(3)
        params["FastEMA"] = int(c4.number_input("Fast EMA", min_value=1, value=int(params.get("FastEMA", 21)), step=1))
        params["SlowEMA"] = int(c5.number_input("Slow EMA", min_value=2, value=int(params.get("SlowEMA", 55)), step=1))
        params["BBWRPeriod"] = int(c6.number_input("BB Width Period", min_value=1, value=int(params.get("BBWRPeriod", 24)), step=1))
        c7, c8, c9 = st.columns(3)
        params["BBWRMin"] = float(c7.number_input("BB Width Min", min_value=0.0, value=float(params.get("BBWRMin", 0.015)), step=0.001, format="%.3f"))
        params["EntryBufferATR"] = float(c8.number_input("Entry Buffer ATR", min_value=0.0, value=float(params.get("EntryBufferATR", 0.15)), step=0.05))
        params["MaxDistancePct"] = float(c9.number_input("Max Distance %", min_value=0.0, value=float(params.get("MaxDistancePct", 3.5)), step=0.1))
        c10, c11, c12 = st.columns(3)
        params["PullbackLookback"] = int(c10.number_input("Pullback Lookback", min_value=1, value=int(params.get("PullbackLookback", 5)), step=1))
        params["TrailATR"] = float(c11.number_input("Trail ATR", min_value=0.1, value=float(params.get("TrailATR", 1.1)), step=0.1))
        params["ExitAfterBars"] = int(c12.number_input("Exit After Bars", min_value=0, value=int(params.get("ExitAfterBars", 18)), step=1))
        c13, c14, c15 = st.columns(3)
        params["PullbackATR"] = float(c13.number_input("Pullback ATR", min_value=0.0, value=float(params.get("PullbackATR", 0.6)), step=0.1))
        params["BreakEvenATR"] = float(c14.number_input("Break-Even ATR", min_value=0.0, value=float(params.get("BreakEvenATR", 0.8)), step=0.1))
        params["TimeStopATR"] = float(c15.number_input("Time Stop ATR", min_value=0.0, value=float(params.get("TimeStopATR", 0.4)), step=0.1))
    elif template_name == "sqx_usdjpy_vwap_wt":
        c1, c2, c3 = st.columns(3)
        params["EMAPeriod1"] = int(c1.number_input("EMA Period", min_value=1, value=int(params.get("EMAPeriod1", 20)), step=1))
        params["VWAPPeriod1"] = int(c2.number_input("VWAP Period", min_value=1, value=int(params.get("VWAPPeriod1", 77)), step=1))
        params["HighestPeriod"] = int(c3.number_input("Highest Period", min_value=1, value=int(params.get("HighestPeriod", 20)), step=1))
        c4, c5, c6 = st.columns(3)
        params["WaveTrendChannel"] = int(c4.number_input("WT Channel", min_value=1, value=int(params.get("WaveTrendChannel", 9)), step=1))
        params["WaveTrendAverage"] = int(c5.number_input("WT Average", min_value=1, value=int(params.get("WaveTrendAverage", 60)), step=1))
        params["PriceEntryMult1"] = float(c6.number_input("Entry Mult", value=float(params.get("PriceEntryMult1", 0.3)), step=0.1))
        c7, c8, c9 = st.columns(3)
        params["IndicatorCrsMAPrd1"] = int(c7.number_input("Exit MA Period", min_value=1, value=int(params.get("IndicatorCrsMAPrd1", 35)), step=1))
        params["ExitAfterBars1"] = int(c8.number_input("Exit After Bars", min_value=0, value=int(params.get("ExitAfterBars1", 14)), step=1))
        params["ATRPeriod1"] = int(c9.number_input("ATR 1", min_value=1, value=int(params.get("ATRPeriod1", 19)), step=1))
        params["ATRPeriod2"] = int(st.number_input("ATR 2", min_value=1, value=int(params.get("ATRPeriod2", 14)), step=1))
    elif template_name == "sqx_hk50_batch_h1":
        c1, c2, c3 = st.columns(3)
        params["LWMAPeriod1"] = int(c1.number_input("LWMA Period", min_value=1, value=int(params.get("LWMAPeriod1", 14)), step=1))
        params["IndicatorCrsMAPrd1"] = int(c2.number_input("Cross MA Period", min_value=1, value=int(params.get("IndicatorCrsMAPrd1", 47)), step=1))
        params["Highest_period"] = int(c3.number_input("Highest Period", min_value=1, value=int(params.get("Highest_period", 50)), step=1))
        c4, c5, c6 = st.columns(3)
        params["Lowest_period"] = int(c4.number_input("Lowest Period", min_value=1, value=int(params.get("Lowest_period", 50)), step=1))
        params["ATR1_period"] = int(c5.number_input("ATR 1", min_value=1, value=int(params.get("ATR1_period", 19)), step=1))
        params["ATR2_period"] = int(c6.number_input("ATR 2", min_value=1, value=int(params.get("ATR2_period", 45)), step=1))
        c7, c8 = st.columns(2)
        params["ATR3_period"] = int(c7.number_input("ATR 3", min_value=1, value=int(params.get("ATR3_period", 14)), step=1))
        params["ATR4_period"] = int(c8.number_input("ATR 4", min_value=1, value=int(params.get("ATR4_period", 100)), step=1))
        t1, t2 = st.columns(2)
        params["SignalTimeRangeFrom"] = t1.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:13")))
        params["SignalTimeRangeTo"] = t2.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "00:26")))
        riskx1, riskx2, riskx3 = st.columns(3)
        params["TrailingActCef1"] = float(riskx1.number_input("Trail Activation", value=float(params.get("TrailingActCef1", 1.4)), step=0.1))
        params["TrailingStop1"] = float(riskx2.number_input("Long Trail Stop", value=float(params.get("TrailingStop1", 127.5)), step=0.1))
        params["TrailingStopCoef1"] = float(riskx3.number_input("Short Trail ATR", value=float(params.get("TrailingStopCoef1", 1.0)), step=0.1))
    elif template_name == "sqx_hk50_after_retest_h4":
        c1, c2, c3 = st.columns(3)
        params["DIPeriod1"] = int(c1.number_input("DI Period", min_value=1, value=int(params.get("DIPeriod1", 14)), step=1))
        params["SARStep"] = float(c2.number_input("SAR Step", min_value=0.001, value=float(params.get("SARStep", 0.266)), step=0.01))
        params["SARMax"] = float(c3.number_input("SAR Max", min_value=0.01, value=float(params.get("SARMax", 0.69)), step=0.01))
        c4, c5, c6 = st.columns(3)
        params["ATRPeriod1"] = int(c4.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod1", 20)), step=1))
        params["PriceEntryMult1"] = float(c5.number_input("Entry ATR Mult", value=float(params.get("PriceEntryMult1", 0.3)), step=0.1))
        params["SignalTimeRangeFrom"] = c6.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:13")))
        params["SignalTimeRangeTo"] = st.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "00:26")))
    elif template_name == "sqx_hk50_before_retest_h4":
        c1, c2, c3 = st.columns(3)
        params["RSIPeriod1"] = int(c1.number_input("RSI Period", min_value=1, value=int(params.get("RSIPeriod1", 14)), step=1))
        params["Period1"] = int(c2.number_input("Range Period", min_value=1, value=int(params.get("Period1", 50)), step=1))
        params["SMAPeriod1"] = int(c3.number_input("SMA Period", min_value=1, value=int(params.get("SMAPeriod1", 20)), step=1))
        c4, c5, c6 = st.columns(3)
        params["ATRPeriod1"] = int(c4.number_input("ATR 1", min_value=1, value=int(params.get("ATRPeriod1", 50)), step=1))
        params["ATRPeriod2"] = int(c5.number_input("ATR 2", min_value=1, value=int(params.get("ATRPeriod2", 19)), step=1))
        params["ATRPeriod3"] = int(c6.number_input("ATR 3", min_value=1, value=int(params.get("ATRPeriod3", 65)), step=1))
        c7, c8, c9 = st.columns(3)
        params["PriceEntryMult1"] = float(c7.number_input("Entry ATR Mult", value=float(params.get("PriceEntryMult1", 0.3)), step=0.1))
        params["ProfitTargetCoef1"] = float(c8.number_input("PT ATR Mult", value=float(params.get("ProfitTargetCoef1", 3.0)), step=0.1))
        params["TrailingActCef1"] = float(c9.number_input("Trail Activation", value=float(params.get("TrailingActCef1", 1.4)), step=0.1))
        t1, t2 = st.columns(2)
        params["SignalTimeRangeFrom"] = t1.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:13")))
        params["SignalTimeRangeTo"] = t2.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "00:26")))
    elif template_name == "sqx_uk100_ulcer_keltner_h1":
        c1, c2, c3 = st.columns(3)
        params["UlcerPeriod"] = int(c1.number_input("Ulcer Period", min_value=1, value=int(params.get("UlcerPeriod", 48)), step=1))
        params["KCPeriod"] = int(c2.number_input("Keltner Period", min_value=1, value=int(params.get("KCPeriod", 20)), step=1))
        params["KCMult1"] = float(c3.number_input("KC Mult 1", min_value=0.1, value=float(params.get("KCMult1", 2.25)), step=0.05))
        c4, c5, c6 = st.columns(3)
        params["KCMult2"] = float(c4.number_input("KC Mult 2", min_value=0.1, value=float(params.get("KCMult2", 2.5)), step=0.05))
        params["ATR1_period"] = int(c5.number_input("ATR 1", min_value=1, value=int(params.get("ATR1_period", 50)), step=1))
        params["ATR2_period"] = int(c6.number_input("ATR 2", min_value=1, value=int(params.get("ATR2_period", 19)), step=1))
        c7, c8, c9 = st.columns(3)
        params["ATR3_period"] = int(c7.number_input("ATR 3", min_value=1, value=int(params.get("ATR3_period", 100)), step=1))
        params["ATR4_period"] = int(c8.number_input("ATR 4", min_value=1, value=int(params.get("ATR4_period", 14)), step=1))
        params["SignalTimeRangeFrom"] = c9.text_input("Signal From", value=str(params.get("SignalTimeRangeFrom", "00:13")))
        params["SignalTimeRangeTo"] = st.text_input("Signal To", value=str(params.get("SignalTimeRangeTo", "00:26")))
    else:
        c1, c2, c3 = st.columns(3)
        params["BBPeriod"] = int(c1.number_input("Bollinger Period", min_value=1, value=int(params.get("BBPeriod", 20)), step=1))
        params["BBDev"] = float(c2.number_input("Bollinger Dev", min_value=0.1, value=float(params.get("BBDev", 2.0)), step=0.1))
        params["WPRPeriod"] = int(c3.number_input("WPR Period", min_value=1, value=int(params.get("WPRPeriod", 14)), step=1))
        c4, c5, c6 = st.columns(3)
        params["WPROversold"] = float(c4.number_input("WPR Oversold", value=float(params.get("WPROversold", -80.0)), step=1.0))
        params["WPROverbought"] = float(c5.number_input("WPR Overbought", value=float(params.get("WPROverbought", -20.0)), step=1.0))
        params["ATRPeriod"] = int(c6.number_input("ATR Period", min_value=1, value=int(params.get("ATRPeriod", 14)), step=1))

    risk1, risk2, risk3 = st.columns(3)
    params["mmLots"] = float(risk1.number_input("Lots", min_value=0.0, value=float(params.get("mmLots", 1.0)), step=0.1))
    params["StopLossATR"] = float(risk2.number_input("Stop Loss ATR", min_value=0.0, value=float(params.get("StopLossATR", 1.5)), step=0.1))
    params["ProfitTargetATR"] = float(risk3.number_input("Take Profit ATR", min_value=0.0, value=float(params.get("ProfitTargetATR", 2.0)), step=0.1))
    return params
