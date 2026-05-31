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

def render_sqx_uk100_ulcer_keltner_h1_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int UlcerPeriod = {parse_int(params.get("UlcerPeriod", 48), 48)};
input int KCPeriod = {parse_int(params.get("KCPeriod", 20), 20)};
input double KCMult1 = {parse_float(params.get("KCMult1", 2.25), 2.25)};
input double KCMult2 = {parse_float(params.get("KCMult2", 2.5), 2.5)};
input int ATR1Period = {parse_int(params.get("ATR1_period", 50), 50)};
input int ATR2Period = {parse_int(params.get("ATR2_period", 19), 19)};
input int ATR3Period = {parse_int(params.get("ATR3_period", 100), 100)};
input int ATR4Period = {parse_int(params.get("ATR4_period", 14), 14)};

input group "Session"
input int SignalFromHour = {parse_int(str(params.get("SignalTimeRangeFrom", "00:13"))[:2], 0)};
input int SignalFromMinute = {parse_int(str(params.get("SignalTimeRangeFrom", "00:13"))[3:], 13)};
input int SignalToHour = {parse_int(str(params.get("SignalTimeRangeTo", "00:26"))[:2], 0)};
input int SignalToMinute = {parse_int(str(params.get("SignalTimeRangeTo", "00:26"))[3:], 26)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
int g_ema_kc1_handle = INVALID_HANDLE;
int g_ema_kc2_handle = INVALID_HANDLE;
int g_kc_atr_handle = INVALID_HANDLE;
int g_atr1_handle = INVALID_HANDLE;
int g_atr2_handle = INVALID_HANDLE;
int g_atr3_handle = INVALID_HANDLE;
int g_atr4_handle = INVALID_HANDLE;

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
   }}
}}

double EmaFromClose(const int shift)
{{
   double value = 0.0;
   return CopyValue(g_ema_kc1_handle, 0, shift, value) ? value : 0.0;
}}

double AtrValue(const int handle, const int shift)
{{
   double value = 0.0;
   return CopyValue(handle, 0, shift, value) ? value : 0.0;
}}

double UlcerIndexValue(const int shift)
{{
   int period = MathMax(UlcerPeriod, 1);
   double rolling_max = -DBL_MAX;
   double sum_sq = 0.0;
   for(int j = 0; j < period; ++j)
   {{
      double max_close = -DBL_MAX;
      for(int k = 0; k < period; ++k)
      {{
         double c = iClose(_Symbol, InpTimeframe, shift + j + k);
         if(c == 0.0)
            continue;
         max_close = MathMax(max_close, c);
      }}
      double close_val = iClose(_Symbol, InpTimeframe, shift + j);
      if(close_val == 0.0 || max_close == -DBL_MAX || max_close == 0.0)
         continue;
      double dd = ((close_val - max_close) / max_close) * 100.0;
      sum_sq += dd * dd;
   }}
   return MathSqrt(sum_sq / period);
}}

bool RisingUlcer2Shift1()
{{
   double u2 = UlcerIndexValue(2);
   double u3 = UlcerIndexValue(3);
   double u4 = UlcerIndexValue(4);
   return (u2 > u3 && u3 > u4);
}}

double KcUpper1(const int shift)
{{
   return EmaFromClose(shift) + KCMult1 * AtrValue(g_kc_atr_handle, shift);
}}

double KcLower1(const int shift)
{{
   return EmaFromClose(shift) - KCMult1 * AtrValue(g_kc_atr_handle, shift);
}}

double KcLower2(const int shift)
{{
   return EmaFromClose(shift) - KCMult2 * AtrValue(g_kc_atr_handle, shift);
}}

double HAOpen(const int shift)
{{
   int bars = shift + 64;
   double ha_open = (iOpen(_Symbol, InpTimeframe, bars - 1) + iClose(_Symbol, InpTimeframe, bars - 1)) / 2.0;
   double ha_close = 0.0;
   for(int idx = bars - 2; idx >= shift; --idx)
   {{
      ha_close = (iOpen(_Symbol, InpTimeframe, idx + 1) + iHigh(_Symbol, InpTimeframe, idx + 1) + iLow(_Symbol, InpTimeframe, idx + 1) + iClose(_Symbol, InpTimeframe, idx + 1)) / 4.0;
      ha_open = (ha_open + ha_close) / 2.0;
   }}
   return ha_open;
}}

double HAClose(const int shift)
{{
   return (iOpen(_Symbol, InpTimeframe, shift) + iHigh(_Symbol, InpTimeframe, shift) + iLow(_Symbol, InpTimeframe, shift) + iClose(_Symbol, InpTimeframe, shift)) / 4.0;
}}

bool ShortExitSignal()
{{
   double curr = KcLower2(3);
   if(curr == 0.0)
      return false;
   int count = 558;
   int usable = 0;
   double values[];
   ArrayResize(values, count);
   for(int i = 0; i < count; ++i)
   {{
      double x = KcLower2(1 + i);
      if(x == 0.0)
         continue;
      values[usable++] = x;
   }}
   if(usable < 50)
      return false;
   ArrayResize(values, usable);
   ArraySort(values);
   int idx = (int)MathFloor(0.532 * (usable - 1));
   idx = MathMax(0, MathMin(idx, usable - 1));
   return curr < values[idx];
}}

bool LongSignal()
{{
   return RisingUlcer2Shift1() && (iClose(_Symbol, InpTimeframe, 1) < KcLower1(1));
}}

bool ShortSignal()
{{
   return RisingUlcer2Shift1() && (iClose(_Symbol, InpTimeframe, 1) > KcUpper1(1));
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_kc1_handle = iMA(_Symbol, InpTimeframe, KCPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_kc2_handle = iMA(_Symbol, InpTimeframe, KCPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_kc_atr_handle = iATR(_Symbol, InpTimeframe, KCPeriod);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATR1Period);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATR2Period);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATR3Period);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATR4Period);
   if(g_ema_kc1_handle == INVALID_HANDLE || g_ema_kc2_handle == INVALID_HANDLE || g_kc_atr_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE || g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ema_kc1_handle != INVALID_HANDLE) IndicatorRelease(g_ema_kc1_handle);
   if(g_ema_kc2_handle != INVALID_HANDLE) IndicatorRelease(g_ema_kc2_handle);
   if(g_kc_atr_handle != INVALID_HANDLE) IndicatorRelease(g_kc_atr_handle);
   if(g_atr1_handle != INVALID_HANDLE) IndicatorRelease(g_atr1_handle);
   if(g_atr2_handle != INVALID_HANDLE) IndicatorRelease(g_atr2_handle);
   if(g_atr3_handle != INVALID_HANDLE) IndicatorRelease(g_atr3_handle);
   if(g_atr4_handle != INVALID_HANDLE) IndicatorRelease(g_atr4_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InTimeWindow(bar_time) && HasOpenPosition())
   {{
      CloseManagedPositions();
      return;
   }}
   if(HasOpenPosition() && ShortExitSignal())
   {{
      CloseManagedPositions();
      return;
   }}

   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr1_3 = AtrValue(g_atr1_handle, 3);
   double atr2_1 = AtrValue(g_atr2_handle, 1);
   double atr3_1 = AtrValue(g_atr3_handle, 1);
   double atr4_1 = AtrValue(g_atr4_handle, 1);
   if(atr1_3 <= 0.0 || atr2_1 <= 0.0 || atr3_1 <= 0.0 || atr4_1 <= 0.0)
      return;

   if(LongSignal())
   {{
      double base = MathMax(iHigh(_Symbol, InpTimeframe, 3), MathMax(HAOpen(3), HAClose(3))) - (2.30 * atr1_3);
      double sl = base - (1.5 * atr2_1);
      double tp = base + (3.5 * atr2_1);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * 6;
      if(trade.BuyStop(InpLots, base, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long"))
         g_long_expiry = expiry;
      return;
   }}

   if(ShortSignal())
   {{
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = iOpen(_Symbol, InpTimeframe, 0) + (2.0 * atr4_1);
      double tp = iOpen(_Symbol, InpTimeframe, 0) - (3.4 * atr4_1);
      if(bid > 0.0)
         trade.Sell(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_short");
   }}
}}
"""
