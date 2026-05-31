from __future__ import annotations
from typing import Any
from config import settings
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    session_hours,
    signal_window_params,
    normalized_export_lots,
    magic_number,
    mt5_timeframe,
    mql_session_window_checks,
    mql_broker_tradable_checks,
)

def render_sqx_usdjpy_vwap_wt_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = payload.get("symbol", "USDJPY")
    mql_tf = mt5_timeframe(payload.get("timeframe", "H4"))
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int EMAPeriod1 = {parse_int(params.get("EMAPeriod1", 34), 34)};
input int VWAPPeriod1 = {parse_int(params.get("VWAPPeriod1", 55), 55)};
input int WaveTrendAverage = {parse_int(params.get("WaveTrendAverage", 60), 60)};
input int WaveTrendChannel = {parse_int(params.get("WaveTrendChannel", 9), 9)};
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 12), 12)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 19), 19)};
input int ATRPeriod2 = {parse_int(params.get("ATRPeriod2", 14), 14)};
input int IndicatorCrsMAPrd1 = {parse_int(params.get("IndicatorCrsMAPrd1", 35), 35)};
input int IndicatorCrsMAPrd2 = {parse_int(params.get("IndicatorCrsMAPrd2", 31), 31)};
input double PriceEntryMult1 = {parse_float(params.get("PriceEntryMult1", 0.3), 0.3)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.8), 2.8)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 3.0), 3.0)};
input int ExitAfterBars1 = {parse_int(params.get("ExitAfterBars1", 14), 14)};

input group "Session"
input int SignalFromHour = 0;
input int SignalFromMinute = 0;
input int SignalToHour = 23;
input int SignalToMinute = 59;

datetime g_last_bar_time = 0;
datetime g_last_trade_bar = 0; // Tracks the bar time of the last opened position to prevent multiple trades per bar
int g_ema_handle = INVALID_HANDLE;
int g_atr1_handle = INVALID_HANDLE;
int g_atr2_handle = INVALID_HANDLE;

bool CopyValue(const int handle, const int buffer, const int shift, double &value)
{{
   double tmp[];
   ArraySetAsSeries(tmp, true);
   if(CopyBuffer(handle, buffer, shift, 1, tmp) < 1)
      return false;
   value = tmp[0];
   return true;
}}

bool IsNewBar()
{{
   datetime current_bar = iTime(_Symbol, InpTimeframe, 0);
   if(current_bar == 0) return false;
   if(current_bar != g_last_bar_time)
   {{
      g_last_bar_time = current_bar;
      return true;
   }}
   return false;
}}

double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iHigh(_Symbol, InpTimeframe, shift);
      if(x == 0.0) continue;
      value = MathMax(value, x);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}

double VWAPVariable(const int shift, const int period)
{{
   double sum_pv = 0.0;
   double sum_v = 0.0;
   for(int i = 0; i < period; ++i)
   {{
      double h = iHigh(_Symbol, InpTimeframe, shift + i);
      double l = iLow(_Symbol, InpTimeframe, shift + i);
      double c = iClose(_Symbol, InpTimeframe, shift + i);
      double v = (double)iVolume(_Symbol, InpTimeframe, shift + i);
      sum_pv += ((h + l + c) / 3.0) * v;
      sum_v += v;
   }}
   return (sum_v == 0.0) ? 0.0 : sum_pv / sum_v;
}}

double SMA_VWAP(const int shift, const int period, const int vwap_period)
{{
   double sum = 0.0;
   for(int i = 0; i < period; ++i)
      sum += VWAPVariable(shift + i, vwap_period);
   return sum / period;
}}

void WaveTrend(const int shift, double &wt_main)
{{
   int channel_len = WaveTrendChannel;
   int avg_len = WaveTrendAverage;
   int lb = MathMax(250, (channel_len + avg_len) * 5 + 20);

   double esa[]; ArraySetAsSeries(esa, true); ArrayResize(esa, lb);
   double d[]; ArraySetAsSeries(d, true); ArrayResize(d, lb);

   for(int i = lb - 1; i >= 0; --i)
   {{
      double cap = (iHigh(_Symbol, InpTimeframe, shift + i) + iLow(_Symbol, InpTimeframe, shift + i) + iClose(_Symbol, InpTimeframe, shift + i)) / 3.0;
      double pesa = (i == lb - 1) ? cap : esa[i + 1];
      esa[i] = pesa + (2.0 / (channel_len + 1.0)) * (cap - pesa);
      double pd = (i == lb - 1) ? 0.0 : d[i + 1];
      d[i] = pd + (2.0 / (channel_len + 1.0)) * (MathAbs(cap - esa[i]) - pd);
   }}

   double ci[]; ArraySetAsSeries(ci, true); ArrayResize(ci, lb);
   for(int i = 0; i < lb; ++i) ci[i] = (iHigh(_Symbol, InpTimeframe, shift+i) + iLow(_Symbol, InpTimeframe, shift+i) + iClose(_Symbol, InpTimeframe, shift+i)) / 3.0 - esa[i];
   for(int i = 0; i < lb; ++i) ci[i] /= (0.015 * d[i] + 1e-9);

   double tci[]; ArraySetAsSeries(tci, true); ArrayResize(tci, lb);
   for(int i = lb - 1; i >= 0; --i)
   {{
      double ptci = (i == lb - 1) ? ci[i] : tci[i + 1];
      tci[i] = ptci + (2.0 / (avg_len + 1.0)) * (ci[i] - ptci);
   }}

   wt_main = tci[0];
}}
bool LongEntrySignal()
{{
   double ema_2 = 0.0;
   if(!CopyValue(g_ema_handle, 0, 2, ema_2)) return false;
   
   for(int i=0; i<5; i++) {{
      double open_i = iOpen(_Symbol, InpTimeframe, i);
      if(open_i > ema_2) return false;
   }}
   return true;
}}

bool LongExitSignal()
{{
   double vwap_3 = VWAPVariable(3, VWAPPeriod1);
   double vwap_sma_3 = SMA_VWAP(3, IndicatorCrsMAPrd1, VWAPPeriod1);
   
   double wt_1 = 0.0;
   WaveTrend(1, wt_1);
   
   return (vwap_3 < vwap_sma_3) && (wt_1 > 0.0);
}}

void CloseAll()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      trade.PositionClose(ticket);
   }}
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_handle = iMA(_Symbol, InpTimeframe, EMAPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   // Match Python sq_atr (Wilder's smoothing)
   g_atr1_handle = iMA(_Symbol, InpTimeframe, ATRPeriod1, 0, MODE_SMMA, iATR(_Symbol, InpTimeframe, 1));
   g_atr2_handle = iMA(_Symbol, InpTimeframe, ATRPeriod2, 0, MODE_SMMA, iATR(_Symbol, InpTimeframe, 1));
   if(g_ema_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}


bool HasPendingOrders()
{{
   for(int idx = OrdersTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = OrderGetTicket(idx);
      if(ticket == 0 || !OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_BUY_LIMIT || type == ORDER_TYPE_SELL_LIMIT)
         return true;
   }}
   return false;
}}

void OnTick()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || (int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      
      // Record that we have a position open for the current bar to prevent re-entry if it closes early
      g_last_trade_bar = iTime(_Symbol, InpTimeframe, 0);

      if(LongExitSignal()) {{
         trade.PositionClose(ticket);
         return;
      }}
      
      datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
      if(iBarShift(_Symbol, InpTimeframe, open_time) >= ExitAfterBars1) {{
         trade.PositionClose(ticket);
         return;
      }}
   }}

   if(!IsNewBar()) return;
   
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);

   // HARD TRADE LIMIT: Max 1 trade per bar.
   // This prevents "loss loops" where a position is opened and stopped out multiple times within a single H4 bar.
   // This is especially important for USDJPY H4 where volatility can trigger multiple entries in a single bar.
   if(PositionsTotal() > 0 || HasPendingOrders() || bar_time <= g_last_trade_bar) return;

   if(LongEntrySignal())
   {{
      double highest_2 = HighestHigh(HighestPeriod, 2);
      double atr1_1 = 0.0, atr2_1 = 0.0;
      CopyValue(g_atr1_handle, 0, 1, atr1_1);
      CopyValue(g_atr2_handle, 0, 1, atr2_1);
      
      double entry = highest_2 + PriceEntryMult1 * atr1_1;
      double sl = entry - StopLossCoef1 * atr2_1;
      double tp = entry + ProfitTargetCoef1 * atr1_1;
      
      trade.BuyStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, TimeCurrent()+17*PeriodSeconds(InpTimeframe), "{strategy_id}_long");
   }}
}}
"""
