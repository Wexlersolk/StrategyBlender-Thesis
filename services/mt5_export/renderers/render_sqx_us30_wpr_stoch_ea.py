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

def render_sqx_us30_wpr_stoch_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int WPRPeriod = {parse_int(params.get("WPRPeriod", 75), 75)};
input int StochK = {parse_int(params.get("StochK", 14), 14)};
input int StochD = {parse_int(params.get("StochD", 3), 3)};
input int StochSlow = {parse_int(params.get("StochSlow", 3), 3)};
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 105), 105)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 105), 105)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 14), 14)};
input int ATRPeriod2 = {parse_int(params.get("ATRPeriod2", 29), 29)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.0), 2.0)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 2.5), 2.5)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.0), 2.0)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 2.5), 2.5)};
input double TrailingStopCoef1 = {parse_float(params.get("TrailingStopCoef1", 1.0), 1.0)};
input double MaxDistancePct = {parse_float(params.get("MaxDistancePct", 6.0), 6.0)};

input group "Session"
input int SignalFromHour = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[:2], 0)};
input int SignalFromMinute = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[3:], 0)};
input int SignalToHour = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[:2], 23)};
input int SignalToMinute = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[3:], 59)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_wpr_handle = INVALID_HANDLE;
int g_stoch_handle = INVALID_HANDLE;
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

bool CopySeries(const int handle, const int buffer, const int shift, const int count, double &values[])
{{
   ArraySetAsSeries(values, true);
   return CopyBuffer(handle, buffer, shift, count, values) >= count;
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
{mql_broker_tradable_checks("HK50.cash")}
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
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_SELL_STOP)
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

void CancelExpiredOrders(const datetime bar_time)
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
      string comment = OrderGetString(ORDER_COMMENT);
      if(type == ORDER_TYPE_BUY_STOP && comment == "{strategy_id}_long" && g_long_expiry != 0 && bar_time >= g_long_expiry)
         trade.OrderDelete(ticket);
      if(type == ORDER_TYPE_SELL_STOP && comment == "{strategy_id}_short" && g_short_expiry != 0 && bar_time >= g_short_expiry)
         trade.OrderDelete(ticket);
   }}
}}

double HighestClose(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iClose(_Symbol, InpTimeframe, shift);
      if(x == 0.0)
         continue;
      value = MathMax(value, x);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}

double LowestClose(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iClose(_Symbol, InpTimeframe, shift);
      if(x == 0.0)
         continue;
      value = MathMin(value, x);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

double WprRef(const int shift)
{{
   double value = 0.0;
   if(!CopyValue(g_wpr_handle, 0, shift + 10, value))
      return 0.0;
   return value;
}}

bool LongSignal()
{{
   double ref_now = WprRef(1);
   int lookback = 250;
   double values[];
   ArrayResize(values, lookback);
   ArraySetAsSeries(values, true);
   for(int i = 0; i < lookback; ++i)
   {{
      values[i] = WprRef(1 + i);
   }}
   ArraySort(values);
   int idx = (int)MathFloor(0.669 * (lookback - 1));
   idx = MathMax(0, MathMin(idx, lookback - 1));
   double threshold = values[idx];
   return ref_now <= threshold;
}}

bool ShortSignal()
{{
   double signal_vals[];
   ArrayResize(signal_vals, 16);
   if(!CopySeries(g_stoch_handle, 1, 4, 16, signal_vals))
      return false;
   for(int i = 0; i < 12; ++i)
   {{
      if(!(signal_vals[i] < signal_vals[i + 1]))
         return false;
   }}
   return true;
}}

void ManageTrailingStops()
{{
   double atr2 = 0.0;
   if(!CopyValue(g_atr2_handle, 0, 1, atr2))
      return;
   double trail_dist = TrailingStopCoef1 * atr2;
   if(trail_dist <= 0.0)
      return;

   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_SELL)
         continue;

      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double new_sl = ask + trail_dist;
      if(sl == 0.0 || new_sl < sl)
         trade.PositionModify(ticket, new_sl, tp);
   }}
}}

bool DistanceOk(const double current_open, const double ref_price)
{{
   if(current_open <= 0.0)
      return false;
   return (MathAbs(ref_price - current_open) / MathMax(MathAbs(current_open), 1e-9) * 100.0) <= MaxDistancePct;
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_wpr_handle = iWPR(_Symbol, InpTimeframe, WPRPeriod);
   g_stoch_handle = iStochastic(_Symbol, InpTimeframe, StochK, StochD, StochSlow, MODE_LWMA, STO_LOWHIGH);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATRPeriod1);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATRPeriod2);
   if(g_wpr_handle == INVALID_HANDLE || g_stoch_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_wpr_handle != INVALID_HANDLE) IndicatorRelease(g_wpr_handle);
   if(g_stoch_handle != INVALID_HANDLE) IndicatorRelease(g_stoch_handle);
   if(g_atr1_handle != INVALID_HANDLE) IndicatorRelease(g_atr1_handle);
   if(g_atr2_handle != INVALID_HANDLE) IndicatorRelease(g_atr2_handle);
}}

void OnTick()
{{
   ManageTrailingStops();

   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InTimeWindow(bar_time) && HasOpenPosition())
   {{
      CloseManagedPositions();
      return;
   }}

   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr1 = 0.0;
   if(!CopyValue(g_atr1_handle, 0, 1, atr1))
      return;

   bool long_signal = LongSignal();
   bool short_signal = ShortSignal();
   double highest_1 = HighestClose(HighestPeriod, 1);
   double lowest_1 = LowestClose(LowestPeriod, 1);
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   datetime long_expiry = bar_time + PeriodSeconds(InpTimeframe) * 25;
   datetime short_expiry = bar_time + PeriodSeconds(InpTimeframe) * 18;

   if(long_signal && !short_signal)
   {{
      double sl = highest_1 - StopLossCoef1 * atr1;
      double tp = highest_1 + ProfitTargetCoef1 * atr1;
      if(trade.BuyStop(InpLots, highest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, long_expiry, "{strategy_id}_long"))
         g_long_expiry = long_expiry;
      return;
   }}

   if(short_signal && !long_signal && DistanceOk(open_0, lowest_1))
   {{
      double sl = lowest_1 + StopLossCoef2 * atr1;
      double tp = lowest_1 - ProfitTargetCoef2 * atr1;
      if(trade.SellStop(InpLots, lowest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, short_expiry, "{strategy_id}_short"))
         g_short_expiry = short_expiry;
   }}
}}
"""
