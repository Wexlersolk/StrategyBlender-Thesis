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

def render_sqx_xau_ao_hour_breakout_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    direction_mode = str(payload.get("direction_mode", "both"))
    allow_long = "true" if direction_mode != "short_only" else "false"
    allow_short = "true" if direction_mode != "long_only" else "false"

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Direction"
input bool InpAllowLong = {allow_long};
input bool InpAllowShort = {allow_short};

input group "Parameters"
input int LWMAPeriod1 = {parse_int(params.get("LWMAPeriod1", 40), 40)};
input int IndicatorMAPeriod1 = {parse_int(params.get("IndicatorMAPeriod1", 67), 67)};
input double AOPercentile = {parse_float(params.get("AOPercentile", 48.9), 48.9)};
input int AOPercentileLookback = {parse_int(params.get("AOPercentileLookback", 829), 829)};
input double AskPercentile = {parse_float(params.get("AskPercentile", 37.3), 37.3)};
input int AskPercentileLookback = {parse_int(params.get("AskPercentileLookback", 841), 841)};
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 200), 200)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 200), 200)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 19), 19)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 5.0), 5.0)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.2), 2.2)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 155.0), 155.0)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.0), 3.0)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 1.8), 1.8)};
input int LongExpiryBars = {parse_int(params.get("LongExpiryBars", 20), 20)};
input int ShortExpiryBars = {parse_int(params.get("ShortExpiryBars", 14), 14)};
input double TickSize = {parse_float(params.get("TickSize", 0.01), 0.01)};

input group "Session"
input int SignalFromHour = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[:2], 0)};
input int SignalFromMinute = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[3:], 0)};
input int SignalToHour = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[:2], 23)};
input int SignalToMinute = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[3:], 59)};
input int FridayExitHour = {parse_int(str(params.get("FridayExitTime", "22:38"))[:2], 22)};
input int FridayExitMinute = {parse_int(str(params.get("FridayExitTime", "22:38"))[3:], 38)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_ao_handle = INVALID_HANDLE;
int g_lwma_open_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;

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

bool FridayExitDue(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   if(dt.day_of_week != 5)
      return false;
   int hhmm = dt.hour * 100 + dt.min;
   int cutoff = FridayExitHour * 100 + FridayExitMinute;
   return hhmm >= cutoff;
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

double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iHigh(_Symbol, InpTimeframe, shift);
      if(x == 0.0)
         continue;
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
      if(x == 0.0)
         continue;
      value = MathMin(value, x);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

bool LowerPercentileFromSeries(const int handle, const int shift, const int bars, const double percentile, const int precision)
{{
   double curr = 0.0;
   if(!CopyValue(handle, 0, shift, curr))
      return false;
   curr = NormalizeDouble(curr, precision);
   int count = 1;
   for(int i = 0; i < bars; ++i)
   {{
      double prev = 0.0;
      if(!CopyValue(handle, 0, shift + i, prev))
         return false;
      prev = NormalizeDouble(prev, precision);
      if(curr < prev)
         count++;
   }}
   double percrank = ((double)count / (double)bars) * 100.0;
   return percrank >= percentile;
}}

bool LowerPercentileFromAsk(const int bars, const double percentile, const int precision)
{{
   double curr = NormalizeDouble(SymbolInfoDouble(_Symbol, SYMBOL_ASK), precision);
   double spread_points = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   int count = 1;
   for(int i = 0; i < bars; ++i)
   {{
      double prev = NormalizeDouble(iOpen(_Symbol, InpTimeframe, 1 + i) + spread_points * TickSize, precision);
      if(curr < prev)
         count++;
   }}
   double percrank = ((double)count / (double)bars) * 100.0;
   return percrank >= percentile;
}}

bool LongSignal()
{{
   if(!InpAllowLong)
      return false;
   if(!LowerPercentileFromSeries(g_ao_handle, 3, AOPercentileLookback, AOPercentile, 5))
      return false;
   double lwma_open_1 = 0.0;
   if(!CopyValue(g_lwma_open_handle, 0, 1, lwma_open_1))
      return false;
   return NormalizeDouble(iHigh(_Symbol, InpTimeframe, 1), 6) > NormalizeDouble(lwma_open_1, 6);
}}

bool ShortSignal()
{{
   if(!InpAllowShort)
      return false;
   MqlDateTime dt;
   TimeToStruct(iTime(_Symbol, InpTimeframe, 3), dt);
   double sum = 0.0;
   for(int i = 0; i < IndicatorMAPeriod1; ++i)
   {{
      MqlDateTime prev_dt;
      TimeToStruct(iTime(_Symbol, InpTimeframe, 3 + i), prev_dt);
      sum += prev_dt.hour;
   }}
   double hour_ma = sum / (double)IndicatorMAPeriod1;
   if(!(dt.hour > hour_ma))
      return false;
   return LowerPercentileFromAsk(AskPercentileLookback, AskPercentile, 5);
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ao_handle = iAO(_Symbol, InpTimeframe);
   g_lwma_open_handle = iMA(_Symbol, InpTimeframe, LWMAPeriod1, 0, MODE_LWMA, PRICE_OPEN);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_ao_handle == INVALID_HANDLE || g_lwma_open_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ao_handle != INVALID_HANDLE) IndicatorRelease(g_ao_handle);
   if(g_lwma_open_handle != INVALID_HANDLE) IndicatorRelease(g_lwma_open_handle);
   if(g_atr_handle != INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(FridayExitDue(bar_time))
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}
   if(!InTimeWindow(bar_time))
   {{
      CancelManagedOrders();
      return;
   }}

   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr_1 = 0.0;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1))
      return;

   double highest_1 = HighestClose(HighestPeriod, 2);
   double lowest_1 = LowestClose(LowestPeriod, 2);
   datetime long_expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
   datetime short_expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;

   if(LongSignal())
   {{
      double sl = highest_1 - StopLossCoef1 * atr_1;
      double tp = highest_1 + ProfitTargetCoef1 * atr_1;
      if(trade.BuyStop(InpLots, highest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, long_expiry, "{strategy_id}_long"))
         g_long_expiry = long_expiry;
      return;
   }}

   if(ShortSignal())
   {{
      double sl = lowest_1 + StopLossCoef2 * atr_1;
      double tp = lowest_1 - ProfitTargetCoef2 * atr_1;
      if(trade.SellStop(InpLots, lowest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, short_expiry, "{strategy_id}_short"))
         g_short_expiry = short_expiry;
   }}
}}
"""
