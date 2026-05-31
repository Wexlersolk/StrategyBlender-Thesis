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

def render_sqx_xau_highest_breakout_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    long_mode = str(payload.get("long_signal_mode", "sma_bias"))
    short_mode = str(payload.get("short_signal_mode", "lwma_lowest_count"))

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "SQX Blocks"
input string InpLongSignalMode = "{long_mode}";
input string InpShortSignalMode = "{short_mode}";

input group "Parameters"
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 245), 245)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 245), 245)};
input int PullbackSignalPeriod = {parse_int(params.get("PullbackSignalPeriod", 10), 10)};
input int FastSMAPeriod = {parse_int(params.get("FastSMAPeriod", 10), 10)};
input int SignalMAPeriod = {parse_int(params.get("SignalMAPeriod", 57), 57)};
input int LWMAPeriod = {parse_int(params.get("LWMAPeriod", 54), 54)};
input int ShortLWMAPeriod = {parse_int(params.get("ShortLWMAPeriod", 14), 14)};
input int SMMAPeriod = {parse_int(params.get("SMMAPeriod", 30), 30)};
input int HAFloorMAPeriod = {parse_int(params.get("HAFloorMAPeriod", 67), 67)};
input int WaveTrendChannel = {parse_int(params.get("WaveTrendChannel", 9), 9)};
input int WaveTrendAverage = {parse_int(params.get("WaveTrendAverage", 21), 21)};
input int ATRLongStopPeriod = {parse_int(params.get("ATRLongStopPeriod", 14), 14)};
input int ATRLongTargetPeriod = {parse_int(params.get("ATRLongTargetPeriod", 14), 14)};
input int ATRLongTrailPeriod = {parse_int(params.get("ATRLongTrailPeriod", 40), 40)};
input int ATRShortStopPeriod = {parse_int(params.get("ATRShortStopPeriod", 14), 14)};
input int ATRShortTargetPeriod = {parse_int(params.get("ATRShortTargetPeriod", 19), 19)};
input double LongStopATR = {parse_float(params.get("LongStopATR", 2.0), 2.0)};
input double LongTargetATR = {parse_float(params.get("LongTargetATR", 3.5), 3.5)};
input double ShortStopATR = {parse_float(params.get("ShortStopATR", 1.5), 1.5)};
input double ShortTargetATR = {parse_float(params.get("ShortTargetATR", 4.8), 4.8)};
input int LongExpiryBars = {parse_int(params.get("LongExpiryBars", 10), 10)};
input int ShortExpiryBars = {parse_int(params.get("ShortExpiryBars", 18), 18)};
input double LongTrailATR = {parse_float(params.get("LongTrailATR", 1.0), 1.0)};
input double LongTrailActivationATR = {parse_float(params.get("LongTrailActivationATR", 0.0), 0.0)};
input double ShortTrailATR = {parse_float(params.get("ShortTrailATR", 0.0), 0.0)};
input double ShortTrailActivationATR = {parse_float(params.get("ShortTrailActivationATR", 0.0), 0.0)};
input int HourQuantileLookback = {parse_int(params.get("HourQuantileLookback", 809), 809)};
input double HourQuantileThreshold = {parse_float(params.get("HourQuantileThreshold", 66.5), 66.5)};
input double MaxDistancePct = {parse_float(params.get("MaxDistancePct", 6.0), 6.0)};

input group "Session"
input int SignalFromHour = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[:2], 0)};
input int SignalFromMinute = {parse_int(str(params.get("SignalTimeRangeFrom", "00:00"))[3:], 0)};
input int SignalToHour = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[:2], 23)};
input int SignalToMinute = {parse_int(str(params.get("SignalTimeRangeTo", "23:59"))[3:], 59)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_sma_fast_handle = INVALID_HANDLE;
int g_lwma_fast_handle = INVALID_HANDLE;
int g_lwma_short_handle = INVALID_HANDLE;
int g_smma_mid_handle = INVALID_HANDLE;
int g_wt_handle = INVALID_HANDLE;
int g_atr_long_stop_handle = INVALID_HANDLE;
int g_atr_long_target_handle = INVALID_HANDLE;
int g_atr_long_trail_handle = INVALID_HANDLE;
int g_atr_short_stop_handle = INVALID_HANDLE;
int g_atr_short_target_handle = INVALID_HANDLE;
int g_ha_handle = INVALID_HANDLE;

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
      if(type == ORDER_TYPE_SELL_STOP && comment == "{strategy_id}_short" && g_short_expiry != 0 && bar_time >= g_short_expiry)
         trade.OrderDelete(ticket);
   }}
}}

double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double high = iHigh(_Symbol, InpTimeframe, shift);
      if(high == 0.0)
         continue;
      value = MathMax(value, high);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}

double LowestLow(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double low = iLow(_Symbol, InpTimeframe, shift);
      if(low == 0.0)
         continue;
      value = MathMin(value, low);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

double TypicalPrice(const int shift)
{{
   return (iHigh(_Symbol, InpTimeframe, shift) + iLow(_Symbol, InpTimeframe, shift) + iClose(_Symbol, InpTimeframe, shift)) / 3.0;
}}

double LowestTypical(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double tp = TypicalPrice(shift);
      if(tp == 0.0)
         continue;
      value = MathMin(value, tp);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

double HeikenAshiFloor(const int shift)
{{
   double ha_open = 0.0;
   double ha_close = 0.0;
   if(!CopyValue(g_ha_handle, 0, shift, ha_open))
      return 0.0;
   if(!CopyValue(g_ha_handle, 3, shift, ha_close))
      return 0.0;
   return MathMin(iLow(_Symbol, InpTimeframe, shift), MathMin(ha_open, ha_close));
}}

double RollingMean(const int handle, const int shift, const int count)
{{
   double values[];
   ArraySetAsSeries(values, true);
   if(CopyBuffer(handle, 0, shift, count, values) < count)
      return 0.0;
   double sum = 0.0;
   for(int i = 0; i < count; ++i)
      sum += values[i];
   return sum / count;
}}

bool DistanceOk(const double current_open, const double ref_price)
{{
   if(current_open <= 0.0 || ref_price <= 0.0)
      return false;
   return (MathAbs(current_open - ref_price) / current_open * 100.0) <= MaxDistancePct;
}}

bool LongSignal()
{{
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   double highest_1 = HighestHigh(HighestPeriod, 2);
   if(!DistanceOk(open_0, highest_1))
      return false;
   if(InpLongSignalMode == "smma_pullback")
   {{
      double smma_2 = 0.0;
      if(!CopyValue(g_smma_mid_handle, 0, 2, smma_2))
         return false;
      return LowestLow(PullbackSignalPeriod, 3) <= smma_2;
   }}
   if(InpLongSignalMode == "ha_reclaim")
   {{
      double floor_1 = HeikenAshiFloor(1);
      if(floor_1 <= 0.0)
         return false;
      double sum = 0.0;
      int count = 0;
      for(int shift = 1; shift <= HAFloorMAPeriod; ++shift)
      {{
         double floor_value = HeikenAshiFloor(shift);
         if(floor_value <= 0.0)
            continue;
         sum += floor_value;
         count++;
      }}
      if(count < 5)
         return false;
      return floor_1 > (sum / count);
   }}
   double sma_3 = 0.0;
   if(!CopyValue(g_sma_fast_handle, 0, 3, sma_3))
      return false;
   double sma_mean = RollingMean(g_sma_fast_handle, 3, SignalMAPeriod);
   if(sma_mean <= 0.0)
      return false;
   return sma_3 > sma_mean;
}}

bool ShortSignal()
{{
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   double lowest_1 = LowestLow(LowestPeriod, 2);
   if(!DistanceOk(open_0, lowest_1))
      return false;
   if(InpShortSignalMode == "wt_push")
   {{
      double wt_1 = 0.0, wt_2 = 0.0;
      double smma_1 = 0.0;
      if(!CopyValue(g_wt_handle, 0, 1, wt_1) || !CopyValue(g_wt_handle, 0, 2, wt_2) || !CopyValue(g_smma_mid_handle, 0, 1, smma_1))
         return false;
      return (iClose(_Symbol, InpTimeframe, 1) > smma_1) && (wt_1 > wt_2);
   }}
   if(InpShortSignalMode == "lwma_hour_quantile")
   {{
      double lwma_short_1 = 0.0;
      if(!CopyValue(g_lwma_short_handle, 0, 1, lwma_short_1))
         return false;
      if(!(lwma_short_1 > iLow(_Symbol, InpTimeframe, 2)))
         return false;
      MqlDateTime dt;
      TimeToStruct(iTime(_Symbol, InpTimeframe, 3), dt);
      double cutoff = (HourQuantileThreshold / 100.0) * 23.0;
      return dt.hour <= cutoff;
   }}
   double lwma_1 = 0.0, lwma_2 = 0.0;
   if(!CopyValue(g_lwma_fast_handle, 0, 1, lwma_1) || !CopyValue(g_lwma_fast_handle, 0, 2, lwma_2))
      return false;
   double lt_3 = LowestTypical(PullbackSignalPeriod, 3);
   double lt_4 = LowestTypical(PullbackSignalPeriod, 4);
   bool ok1 = (lwma_1 <= lt_3);
   bool ok2 = (lwma_2 <= lt_4);
   bool strict = (lwma_1 < lt_3) || (lwma_2 < lt_4);
   return ok1 && ok2 && strict;
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_sma_fast_handle = iMA(_Symbol, InpTimeframe, FastSMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   g_lwma_fast_handle = iMA(_Symbol, InpTimeframe, LWMAPeriod, 0, MODE_LWMA, PRICE_CLOSE);
   g_lwma_short_handle = iMA(_Symbol, InpTimeframe, ShortLWMAPeriod, 0, MODE_LWMA, PRICE_CLOSE);
   g_smma_mid_handle = iMA(_Symbol, InpTimeframe, SMMAPeriod, 0, MODE_SMMA, PRICE_MEDIAN);
   g_wt_handle = iCustom(_Symbol, InpTimeframe, "SqWaveTrend", WaveTrendChannel, WaveTrendAverage);
   g_atr_long_stop_handle = iATR(_Symbol, InpTimeframe, ATRLongStopPeriod);
   g_atr_long_target_handle = iATR(_Symbol, InpTimeframe, ATRLongTargetPeriod);
   g_atr_long_trail_handle = iATR(_Symbol, InpTimeframe, ATRLongTrailPeriod);
   g_atr_short_stop_handle = iATR(_Symbol, InpTimeframe, ATRShortStopPeriod);
   g_atr_short_target_handle = iATR(_Symbol, InpTimeframe, ATRShortTargetPeriod);
   g_ha_handle = iCustom(_Symbol, InpTimeframe, "SqHeikenAshi");
   if(g_sma_fast_handle == INVALID_HANDLE || g_lwma_fast_handle == INVALID_HANDLE || g_lwma_short_handle == INVALID_HANDLE || g_smma_mid_handle == INVALID_HANDLE || g_wt_handle == INVALID_HANDLE || g_atr_long_stop_handle == INVALID_HANDLE || g_atr_long_target_handle == INVALID_HANDLE || g_atr_long_trail_handle == INVALID_HANDLE || g_atr_short_stop_handle == INVALID_HANDLE || g_atr_short_target_handle == INVALID_HANDLE || g_ha_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_sma_fast_handle != INVALID_HANDLE) IndicatorRelease(g_sma_fast_handle);
   if(g_lwma_fast_handle != INVALID_HANDLE) IndicatorRelease(g_lwma_fast_handle);
   if(g_lwma_short_handle != INVALID_HANDLE) IndicatorRelease(g_lwma_short_handle);
   if(g_smma_mid_handle != INVALID_HANDLE) IndicatorRelease(g_smma_mid_handle);
   if(g_wt_handle != INVALID_HANDLE) IndicatorRelease(g_wt_handle);
   if(g_atr_long_stop_handle != INVALID_HANDLE) IndicatorRelease(g_atr_long_stop_handle);
   if(g_atr_long_target_handle != INVALID_HANDLE) IndicatorRelease(g_atr_long_target_handle);
   if(g_atr_long_trail_handle != INVALID_HANDLE) IndicatorRelease(g_atr_long_trail_handle);
   if(g_atr_short_stop_handle != INVALID_HANDLE) IndicatorRelease(g_atr_short_stop_handle);
   if(g_atr_short_target_handle != INVALID_HANDLE) IndicatorRelease(g_atr_short_target_handle);
   if(g_ha_handle != INVALID_HANDLE) IndicatorRelease(g_ha_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InTimeWindow(bar_time))
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}
   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr_long_stop = 0.0, atr_long_target = 0.0, atr_long_trail = 0.0, atr_short_stop = 0.0, atr_short_target = 0.0;
   if(!CopyValue(g_atr_long_stop_handle, 0, 1, atr_long_stop) || !CopyValue(g_atr_long_target_handle, 0, 1, atr_long_target) || !CopyValue(g_atr_long_trail_handle, 0, 1, atr_long_trail) || !CopyValue(g_atr_short_stop_handle, 0, 1, atr_short_stop) || !CopyValue(g_atr_short_target_handle, 0, 1, atr_short_target))
      return;

   double highest_1 = HighestHigh(HighestPeriod, 2);
   double lowest_1 = LowestLow(LowestPeriod, 2);
   datetime long_expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
   datetime short_expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;

   if(LongSignal())
   {{
      double sl = highest_1 - LongStopATR * atr_long_stop;
      double tp = highest_1 + LongTargetATR * atr_long_target;
      if(trade.BuyStop(InpLots, highest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, long_expiry, "{strategy_id}_long"))
         g_long_expiry = long_expiry;
      return;
   }}
   if(ShortSignal())
   {{
      double sl = lowest_1 + ShortStopATR * atr_short_stop;
      double tp = lowest_1 - ShortTargetATR * atr_short_target;
      if(trade.SellStop(InpLots, lowest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, short_expiry, "{strategy_id}_short"))
         g_short_expiry = short_expiry;
   }}
}}
"""
