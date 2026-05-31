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

def render_sqx_hk50_reversion_h1_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = payload.get("symbol", "HK50.cash")
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(symbol, params, default=45.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int BBPeriod = {parse_int(params.get("BBPeriod1", 20), 20)};
input double BBDev = {parse_float(params.get("BBDev1", 2.0), 2.0)};
input int WPRPeriod = {parse_int(params.get("WPRPeriod1", 14), 14)};
input double WPRUpper = {parse_float(params.get("WPRUpper", -20.0), -20.0)};
input double WPRLower = {parse_float(params.get("WPRLower", -80.0), -80.0)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod1", 14), 14)};
input double StopLossCoef = {parse_float(params.get("StopLossCoef1", 1.5), 1.5)};
input double ProfitTargetCoef = {parse_float(params.get("ProfitTargetCoef1", 1.2), 1.2)};

input group "Session"
input int SignalFromHour = {parse_int(str(params.get("SignalTimeRangeFrom", "04:25"))[:2], 4)};
input int SignalFromMinute = {parse_int(str(params.get("SignalTimeRangeFrom", "04:25"))[3:], 25)};
input int SignalToHour = {parse_int(str(params.get("SignalTimeRangeTo", "11:00"))[:2], 11)};
input int SignalToMinute = {parse_int(str(params.get("SignalTimeRangeTo", "11:00"))[3:], 0)};
input int FridayExitHour = {parse_int(str(params.get("FridayExitTime", "11:30"))[:2], 11)};
input int FridayExitMinute = {parse_int(str(params.get("FridayExitTime", "11:30"))[3:], 30)};

datetime g_last_bar_time = 0;
int g_bb_handle = INVALID_HANDLE;
int g_wpr_handle = INVALID_HANDLE;
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
   if(current_bar == 0) return false;
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
   if(dt.day_of_week != 5) return false;
   int hhmm = dt.hour * 100 + dt.min;
   int exit_hhmm = FridayExitHour * 100 + FridayExitMinute;
   return hhmm >= exit_hhmm;
}}

void CloseManagedPositions()
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
   g_bb_handle = iBands(_Symbol, InpTimeframe, BBPeriod, 0, BBDev, PRICE_CLOSE);
   g_wpr_handle = iWPR(_Symbol, InpTimeframe, WPRPeriod);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_bb_handle == INVALID_HANDLE || g_wpr_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(g_bb_handle);
   IndicatorRelease(g_wpr_handle);
   IndicatorRelease(g_atr_handle);
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
   if(!IsNewBar()) return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(IsFridayExitTime(bar_time))
   {{
      CloseManagedPositions();
      return;
   }}

   if(!InTimeWindow(bar_time)) return;

   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      if(PositionSelectByTicket(PositionGetTicket(idx)))
      {{
         if(PositionGetString(POSITION_SYMBOL) == _Symbol && (int)PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
            return;
      }}
   }}

   double bb_lower = 0.0, bb_upper = 0.0, wpr = 0.0, atr = 0.0;
   if(!CopyValue(g_bb_handle, 2, 1, bb_lower) || !CopyValue(g_bb_handle, 1, 1, bb_upper) || 
      !CopyValue(g_wpr_handle, 0, 1, wpr) || !CopyValue(g_atr_handle, 0, 1, atr))
      return;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);

   if(close_1 < bb_lower && wpr < WPRLower)
   {{
      double sl = open_0 - (StopLossCoef * atr);
      double tp = open_0 + (ProfitTargetCoef * atr);
      trade.Buy(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_long");
   }}
   else if(close_1 > bb_upper && wpr > WPRUpper)
   {{
      double sl = open_0 + (StopLossCoef * atr);
      double tp = open_0 - (ProfitTargetCoef * atr);
      trade.Sell(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_short");
   }}
}}
"""
