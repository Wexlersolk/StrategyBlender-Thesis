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

def render_sqx_hk50_ichi_heiken_h1_ea(strategy_id: str, payload: dict[str, Any]) -> str:
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
input int IchimokuTenkanPrd1 = {parse_int(params.get("IchimokuTenkanPrd1", 9), 9)};
input int IchimokuKijunPeriod1 = {parse_int(params.get("IchimokuKijunPeriod1", 26), 26)};
input int IchimokuSenkouPrd1 = {parse_int(params.get("IchimokuSenkouPrd1", 52), 52)};
input int IndicatorMAPeriod1 = {parse_int(params.get("IndicatorMAPeriod1", 72), 72)};
input int HighestPeriod = {parse_int(params.get("Highest_period", 50), 50)};
input int LowestPeriod = {parse_int(params.get("Lowest_period", 60), 60)};
input int ATRFastPeriod = {parse_int(params.get("ATRFastPeriod", 14), 14)};
input int ATRSlowPeriod = {parse_int(params.get("ATRSlowPeriod", 19), 19)};
input double EntryBufferATR = {parse_float(params.get("EntryBufferATR", 0.12), 0.12)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 1.6), 1.6)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 4.8), 4.8)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.6), 2.6)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 2.4), 2.4)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 13)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 0)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 35)};
input int FridayExitHour = {parse_int(str(params.get("FridayExitTime", "22:38"))[:2], 22)};
input int FridayExitMinute = {parse_int(str(params.get("FridayExitTime", "22:38"))[3:], 38)};

datetime g_last_bar_time = 0;
int g_ichi_handle = INVALID_HANDLE;
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

void ComputeHeikenAshiShift(const int target_shift, double &ha_open, double &ha_close)
{{
   int total_bars = Bars(_Symbol, InpTimeframe);
   if(total_bars <= target_shift + 64)
   {{
      ha_open = iOpen(_Symbol, InpTimeframe, target_shift);
      ha_close = iClose(_Symbol, InpTimeframe, target_shift);
      return;
   }}
   int start_shift = target_shift + 60;
   double prev_ha_open = iOpen(_Symbol, InpTimeframe, start_shift + 1);
   double prev_ha_close = iClose(_Symbol, InpTimeframe, start_shift + 1);
   for(int shift = start_shift; shift >= target_shift; --shift)
   {{
      ha_close = (iOpen(_Symbol, InpTimeframe, shift) + iHigh(_Symbol, InpTimeframe, shift) + iLow(_Symbol, InpTimeframe, shift) + iClose(_Symbol, InpTimeframe, shift)) / 4.0;
      ha_open = (prev_ha_open + prev_ha_close) / 2.0;
      prev_ha_open = ha_open;
      prev_ha_close = ha_close;
   }}
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

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ichi_handle = iIchimoku(_Symbol, InpTimeframe, IchimokuTenkanPrd1, IchimokuKijunPeriod1, IchimokuSenkouPrd1);
   g_ema_bias_handle = iMA(_Symbol, InpTimeframe, IndicatorMAPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_fast_handle = iATR(_Symbol, InpTimeframe, ATRFastPeriod);
   g_atr_slow_handle = iATR(_Symbol, InpTimeframe, ATRSlowPeriod);
   if(g_ichi_handle == INVALID_HANDLE || g_ema_bias_handle == INVALID_HANDLE || g_atr_fast_handle == INVALID_HANDLE || g_atr_slow_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ichi_handle != INVALID_HANDLE) IndicatorRelease(g_ichi_handle);
   if(g_ema_bias_handle != INVALID_HANDLE) IndicatorRelease(g_ema_bias_handle);
   if(g_atr_fast_handle != INVALID_HANDLE) IndicatorRelease(g_atr_fast_handle);
   if(g_atr_slow_handle != INVALID_HANDLE) IndicatorRelease(g_atr_slow_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(IsFridayExitTime(bar_time))
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}

   double ha_open_1 = 0.0, ha_close_1 = 0.0;
   ComputeHeikenAshiShift(1, ha_open_1, ha_close_1);

   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      if(pos_type == POSITION_TYPE_BUY && ha_close_1 < ha_open_1)
         trade.PositionClose(ticket);
      if(pos_type == POSITION_TYPE_SELL && ha_close_1 > ha_open_1)
         trade.PositionClose(ticket);
   }}

   if(!InTimeWindow(bar_time) && HasOpenPosition())
   {{
      CloseManagedPositions();
      return;
   }}

   CancelManagedOrders();
   if(HasOpenPosition() || HasPendingOrders() || !InTimeWindow(bar_time))
      return;

   double kijun_1 = 0.0, ema_bias_1 = 0.0, atr_fast_1 = 0.0, atr_slow_1 = 0.0;
   if(!CopyValue(g_ichi_handle, 1, 1, kijun_1) || !CopyValue(g_ema_bias_handle, 0, 1, ema_bias_1) || !CopyValue(g_atr_fast_handle, 0, 1, atr_fast_1) || !CopyValue(g_atr_slow_handle, 0, 1, atr_slow_1))
      return;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   bool long_signal = (close_1 > kijun_1) && (ha_close_1 > ha_open_1) && (close_1 > ema_bias_1);
   bool short_signal = (close_1 < kijun_1) && (ha_close_1 < ha_open_1) && (close_1 < ema_bias_1);

   double highest_1 = HighestHigh(HighestPeriod, 1);
   double lowest_1 = LowestLow(LowestPeriod, 1);
   datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * 2;

   if(long_signal && !short_signal)
   {{
      double base = highest_1 + EntryBufferATR * atr_fast_1;
      double sl = base - StopLossCoef1 * atr_fast_1;
      double tp = base + ProfitTargetCoef1 * atr_slow_1;
      trade.BuyStop(InpLots, base, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double base = lowest_1 - EntryBufferATR * atr_fast_1;
      double sl = base + StopLossCoef2 * atr_fast_1;
      double tp = base - ProfitTargetCoef2 * atr_slow_1;
      trade.SellStop(InpLots, base, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
   }}
}}
"""
