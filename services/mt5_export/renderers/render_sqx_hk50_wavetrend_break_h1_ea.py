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

def render_sqx_hk50_wavetrend_break_h1_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = payload.get("symbol", "HK50.cash")
    signal_from, signal_to = signal_window_params(
        symbol,
        params,
        default_from="00:13",
        default_to="00:35",
    )
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(symbol, params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int WaveTrendChannelLng1 = {parse_int(params.get("WaveTrendChannelLng1", 14), 14)};
input int WaveTrendAverageLng1 = {parse_int(params.get("WaveTrendAverageLng1", 21), 21)};
input int EMAPeriod1 = {parse_int(params.get("EMAPeriod1", 40), 40)};
input int HighestPeriod = {parse_int(params.get("Highest_period", 35), 35)};
input int LowestPeriod = {parse_int(params.get("Lowest_period", 35), 35)};
input int ATRFastPeriod = {parse_int(params.get("ATRFastPeriod", 14), 14)};
input int ATRSlowPeriod = {parse_int(params.get("ATRSlowPeriod", 19), 19)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.1), 2.1)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 5.2), 5.2)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.2), 2.2)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.0), 3.0)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 155.0), 155.0)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 13)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 0)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 35)};
input int FridayExitHour = {parse_int(str(params.get("FridayExitTime", "22:38"))[:2], 22)};
input int FridayExitMinute = {parse_int(str(params.get("FridayExitTime", "22:38"))[3:], 38)};

datetime g_last_bar_time = 0;
int g_ema_bias_handle = INVALID_HANDLE;
int g_atr_fast_handle = INVALID_HANDLE;
int g_atr_slow_handle = INVALID_HANDLE;

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
   if(current_bar == 0)
      return false;
   if(current_bar != g_last_bar_time)
   {{
      g_last_bar_time = current_bar;
      return true;
   }}
   return false;
}}

bool InBrokerTradableWindow(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   int hhmm = dt.hour * 100 + dt.min;
{mql_broker_tradable_checks(symbol)}
}}

bool InTimeWindow(const datetime when)
{{
   if(!InBrokerTradableWindow(when)) return false;
   MqlDateTime dt;
   TimeToStruct(when, dt);
   int hhmm = dt.hour * 100 + dt.min;
   int from_hhmm = SignalFromHour * 100 + SignalFromMinute;
   int to_hhmm = SignalToHour * 100 + SignalToMinute;
   if(from_hhmm <= to_hhmm)
      return (hhmm >= from_hhmm && hhmm <= to_hhmm);
   return (hhmm >= from_hhmm || hhmm <= to_hhmm);
}}

bool IsFridayExitTime(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   if(dt.day_of_week != 5)
      return false;
   int hhmm = dt.hour * 100 + dt.min;
   int exit_hhmm = FridayExitHour * 100 + FridayExitMinute;
   return hhmm >= exit_hhmm;
}}

bool HasOpenPosition()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      return true;
   }}
   return false;
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
      return true;
   }}
   return false;
}}

void CloseManagedPositions()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      trade.PositionClose(ticket);
   }}
}}

void CancelManagedOrders()
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
      trade.OrderDelete(ticket);
   }}
}}

double WaveTrendMain(const int shift)
{{
   int channel_len = WaveTrendChannelLng1;
   int avg_len = WaveTrendAverageLng1;
   int lb = MathMax(250, (channel_len + avg_len) * 5 + 10);

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
   
   return tci[0];
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

double LowestLow(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iLow(_Symbol, InpTimeframe, shift);
      if(x == 0.0) continue;
      value = MathMin(value, x);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

void ManageTrailingStops()
{{
   if(TrailingStop1 <= 0.0) return;
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {{
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double new_sl = bid - TrailingStop1;
         if(sl == 0.0 || new_sl > sl) trade.PositionModify(ticket, new_sl, tp);
      }}
      else
      {{
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double new_sl = ask + TrailingStop1;
         if(sl == 0.0 || new_sl < sl) trade.PositionModify(ticket, new_sl, tp);
      }}
   }}
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_bias_handle = iMA(_Symbol, InpTimeframe, EMAPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_fast_handle = iATR(_Symbol, InpTimeframe, ATRFastPeriod);
   g_atr_slow_handle = iATR(_Symbol, InpTimeframe, ATRSlowPeriod);
   if(g_ema_bias_handle == INVALID_HANDLE || g_atr_fast_handle == INVALID_HANDLE || g_atr_slow_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ema_bias_handle != INVALID_HANDLE) IndicatorRelease(g_ema_bias_handle);
   if(g_atr_fast_handle != INVALID_HANDLE) IndicatorRelease(g_atr_fast_handle);
   if(g_atr_slow_handle != INVALID_HANDLE) IndicatorRelease(g_atr_slow_handle);
}}

void OnTick()
{{
   ManageTrailingStops();
   if(!IsNewBar()) return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(IsFridayExitTime(bar_time))
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}

   if(!InTimeWindow(bar_time) && HasOpenPosition())
   {{
      CloseManagedPositions();
      return;
   }}

   CancelManagedOrders();
   if(HasOpenPosition() || HasPendingOrders() || !InTimeWindow(bar_time))
      return;

   double wt_1 = WaveTrendMain(1);
   double ema_bias_1 = 0.0, atr_fast_1 = 0.0, atr_slow_1 = 0.0;
   if(!CopyValue(g_ema_bias_handle, 0, 1, ema_bias_1) || !CopyValue(g_atr_fast_handle, 0, 1, atr_fast_1) || !CopyValue(g_atr_slow_handle, 0, 1, atr_slow_1))
      return;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double close_2 = iClose(_Symbol, InpTimeframe, 2);
   double close_3 = iClose(_Symbol, InpTimeframe, 3);
   
   bool rising = close_1 > close_2 && close_2 > close_3;
   bool falling = close_1 < close_2 && close_2 < close_3;
   
   bool long_signal = (wt_1 > 0.0) && (close_1 > ema_bias_1) && rising;
   bool short_signal = (wt_1 < 0.0) && (close_1 < ema_bias_1) && falling;

   double highest_1 = HighestHigh(HighestPeriod, 1);
   double lowest_1 = LowestLow(LowestPeriod, 1);
   datetime expiry = bar_time + PeriodSeconds(InpTimeframe);

   if(long_signal && !short_signal)
   {{
      double sl = highest_1 - StopLossCoef1 * atr_fast_1;
      double tp = highest_1 + ProfitTargetCoef1 * atr_slow_1;
      trade.BuyStop(InpLots, highest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double sl = lowest_1 + StopLossCoef2 * atr_fast_1;
      double tp = lowest_1 - ProfitTargetCoef2 * atr_slow_1;
      trade.SellStop(InpLots, lowest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
   }}
}}
"""
