from __future__ import annotations
from typing import Any
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    normalized_export_lots,
    magic_number,
    mt5_timeframe,
    mql_broker_tradable_checks,
    mql_session_window_checks,
)

def render_session_breakout_extreme_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    symbol = str(payload.get("symbol", ""))
    
    start_str = str(params.get("BreakoutStart", "08:00"))
    end_str = str(params.get("BreakoutEnd", "16:00"))
    
    windows = {day: [(start_str, end_str)] for day in range(1, 6)}
    
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=0.1, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int SessionHighLowPeriod = {parse_int(params.get("SessionHighLowPeriod", 20), 20)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int ADXPeriod = {parse_int(params.get("ADXPeriod", 14), 14)};
input double ADXFilterLevel = {parse_float(params.get("ADXFilterLevel", 20.0), 20.0)};
input double EntryBufferATR = {parse_float(params.get("EntryBufferATR", 0.1), 0.1)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 4.0), 4.0)};

int g_atr_handle = INVALID_HANDLE;
int g_adx_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;

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

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   g_adx_handle = iADX(_Symbol, InpTimeframe, ADXPeriod);
   
   if(g_atr_handle == INVALID_HANDLE || g_adx_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

bool CopyValue(const int handle, const int buffer, const int shift, double &value)
{{
   double tmp[];
   ArraySetAsSeries(tmp, true);
   if(CopyBuffer(handle, buffer, shift, 1, tmp) < 1) return false;
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

void OnDeinit(const int reason)
{{
   if(g_atr_handle != INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   if(g_adx_handle != INVALID_HANDLE)
      IndicatorRelease(g_adx_handle);
}}

bool InBrokerTradableWindow(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   int hhmm = dt.hour * 100 + dt.min;
{mql_broker_tradable_checks(symbol)}
}}

bool IsBreakoutStartTime(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   int hhmm = dt.hour * 100 + dt.min;
   int start_hhmm = (int)StringToInteger(StringSubstr("{start_str}", 0, 2)) * 100 + (int)StringToInteger(StringSubstr("{start_str}", 3, 2));
   return hhmm == start_hhmm;
}}

double MinStopDistance()
{{
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;
   return MathMax((double)stops_level * point, point);
}}

bool PlaceLongStop(const double reference_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return false;
   double entry = MathMax(reference_price, ask + MinStopDistance());
   return trade.BuyStop(InpLots, NormalizeDouble(entry, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
}}

bool PlaceShortStop(const double reference_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   double entry = MathMin(reference_price, bid - MinStopDistance());
   return trade.SellStop(InpLots, NormalizeDouble(entry, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
}}

bool HasOpenPosition()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
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

void CancelAllPending()
{{
   for(int idx = OrdersTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = OrderGetTicket(idx);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber) continue;
      trade.OrderDelete(ticket);
   }}
}}

void OnTick()
{{
   if(HasOpenPosition())
   {{
      if(HasPendingOrders())
      {{
         CancelAllPending();
      }}
      return;
   }}

   if(!IsNewBar()) return;
   
   datetime current_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InBrokerTradableWindow(current_time)) return;

   if(HasPendingOrders()) return;

   if(!IsBreakoutStartTime(current_time)) return;

   double adx_1 = 0.0;
   if(!CopyValue(g_adx_handle, 0, 1, adx_1)) return;
   if(adx_1 < ADXFilterLevel) return;

   double atr_1 = 0.0;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;
   
   double session_high = HighestHigh(SessionHighLowPeriod, 1);
   double session_low = LowestLow(SessionHighLowPeriod, 1);

   if(session_high > 0.0)
   {{
      double entry_price = session_high + EntryBufferATR * atr_1;
      double sl = entry_price - StopLossATR * atr_1;
      double tp = entry_price + ProfitTargetATR * atr_1;
      datetime expiry = current_time + PeriodSeconds(InpTimeframe) * 5;
      PlaceLongStop(entry_price, sl, tp, expiry);
   }}
   
   if(session_low > 0.0)
   {{
      double entry_price = session_low - EntryBufferATR * atr_1;
      double sl = entry_price + StopLossATR * atr_1;
      double tp = entry_price - ProfitTargetATR * atr_1;
      datetime expiry = current_time + PeriodSeconds(InpTimeframe) * 5;
      PlaceShortStop(entry_price, sl, tp, expiry);
   }}
}}
"""
