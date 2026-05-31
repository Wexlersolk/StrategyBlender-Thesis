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

def render_sqx_hk50_batch_h1_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    long_signal_mode = str(payload.get("long_signal_mode", "ao_cross")).strip().lower() or "ao_cross"
    short_signal_mode = str(payload.get("short_signal_mode", "lwma_cross")).strip().lower() or "lwma_cross"
    friday_flat_hhmm = str(settings.symbol_execution_defaults("HK50.cash").get("force_flat_hhmm", "11:30"))
    friday_flat_hour = parse_int(friday_flat_hhmm[:2], 11)
    friday_flat_minute = parse_int(friday_flat_hhmm[3:], 30)
    hk50_defaults = settings.symbol_execution_defaults("HK50.cash")
    broker_window_checks = mql_session_window_checks(hk50_defaults.get("tradable_session_windows", {}))
    signal_from, signal_to = signal_window_params(
        payload.get("symbol"),
        params,
        default_from="00:13",
        default_to="00:26",
    )
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol"), params, default=70.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.5), 2.5)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 2.8), 2.8)};
input double TrailingActCef1 = {parse_float(params.get("TrailingActCef1", 1.4), 1.4)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 127.5), 127.5)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 3.0), 3.0)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 2.2), 2.2)};
input double TrailingStopCoef1 = {parse_float(params.get("TrailingStopCoef1", 1.0), 1.0)};
input int LWMAPeriod1 = {parse_int(params.get("LWMAPeriod1", 14), 14)};
input int IndicatorCrsMAPrd1 = {parse_int(params.get("IndicatorCrsMAPrd1", 47), 47)};
input int ATR1Period = {parse_int(params.get("ATR1_period", 19), 19)};
input int ATR2Period = {parse_int(params.get("ATR2_period", 45), 45)};
input int ATR3Period = {parse_int(params.get("ATR3_period", 14), 14)};
input int ATR4Period = {parse_int(params.get("ATR4_period", 100), 100)};
input int HighestPeriod = {parse_int(params.get("Highest_period", 50), 50)};
input int LowestPeriod = {parse_int(params.get("Lowest_period", 50), 50)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 0)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 23)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 59)};
input int FridayFlatHour = {friday_flat_hour};
input int FridayFlatMinute = {friday_flat_minute};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_ao_handle = INVALID_HANDLE;
int g_lwma_handle = INVALID_HANDLE;
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

bool IsFridayForceFlatTime(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   if(dt.day_of_week != 5)
      return false;
   int hhmm = dt.hour * 100 + dt.min;
   int exit_hhmm = FridayFlatHour * 100 + FridayFlatMinute;
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

bool ComputeEMAFromSeries(const double &series[], const int count, const int period, double &ema_curr, double &ema_prev)
{{
   if(count <= period)
      return false;
   double alpha = 2.0 / (period + 1.0);
   double ema = series[count - 1];
   ema_curr = ema;
   ema_prev = ema;
   for(int idx = count - 2; idx >= 0; --idx)
   {{
      ema = alpha * series[idx] + (1.0 - alpha) * ema;
      if(idx == 1)
         ema_prev = ema;
      if(idx == 0)
         ema_curr = ema;
   }}
   return true;
}}

bool LongSignal()
{{
   if("{long_signal_mode}" == "range_break")
   {{
      int count = IndicatorCrsMAPrd1 + 3;
      double lwma_vals[];
      ArrayResize(lwma_vals, count);
      ArraySetAsSeries(lwma_vals, true);
      if(CopyBuffer(g_lwma_handle, 0, 1, count, lwma_vals) < count)
         return false;

      double ema_1 = 0.0, ema_2 = 0.0;
      if(!ComputeEMAFromSeries(lwma_vals, count, IndicatorCrsMAPrd1, ema_1, ema_2))
         return false;

      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      double highest_prev = HighestClose(HighestPeriod, 2);
      return close_1 > highest_prev && lwma_vals[0] > ema_1;
   }}
   if("{long_signal_mode}" == "opening_drive")
   {{
      double ao_1 = 0.0;
      if(!CopyValue(g_ao_handle, 0, 1, ao_1))
         return false;
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      double close_2 = iClose(_Symbol, InpTimeframe, 2);
      double close_3 = iClose(_Symbol, InpTimeframe, 3);
      double lwma_1 = 0.0;
      if(!CopyValue(g_lwma_handle, 0, 1, lwma_1))
         return false;
      return ao_1 > 0.0 && close_1 > lwma_1 && close_1 > close_2 && close_2 > close_3;
   }}
   double ao_1 = 0.0, ao_2 = 0.0;
   if(!CopyValue(g_ao_handle, 0, 1, ao_1) || !CopyValue(g_ao_handle, 0, 2, ao_2))
      return false;
   return ao_1 > 0.0 && ao_2 <= 0.0;
}}

bool ShortSignal()
{{
   if("{short_signal_mode}" == "range_break")
   {{
      int count = IndicatorCrsMAPrd1 + 3;
      double lwma_vals[];
      ArrayResize(lwma_vals, count);
      ArraySetAsSeries(lwma_vals, true);
      if(CopyBuffer(g_lwma_handle, 0, 1, count, lwma_vals) < count)
         return false;

      double ema_1 = 0.0, ema_2 = 0.0;
      if(!ComputeEMAFromSeries(lwma_vals, count, IndicatorCrsMAPrd1, ema_1, ema_2))
         return false;

      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      double lowest_prev = LowestClose(LowestPeriod, 2);
      return close_1 < lowest_prev && lwma_vals[0] < ema_1;
   }}
   if("{short_signal_mode}" == "opening_reversal")
   {{
      double ao_1 = 0.0;
      if(!CopyValue(g_ao_handle, 0, 1, ao_1))
         return false;
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      double close_2 = iClose(_Symbol, InpTimeframe, 2);
      double close_3 = iClose(_Symbol, InpTimeframe, 3);
      double lwma_1 = 0.0;
      if(!CopyValue(g_lwma_handle, 0, 1, lwma_1))
         return false;
      return ao_1 < 0.0 && close_1 < lwma_1 && close_1 < close_2 && close_2 < close_3;
   }}
    int count = IndicatorCrsMAPrd1 + 3;
    double lwma_vals[];
    ArrayResize(lwma_vals, count);
   ArraySetAsSeries(lwma_vals, true);
   if(CopyBuffer(g_lwma_handle, 0, 1, count, lwma_vals) < count)
      return false;

   double ema_1 = 0.0, ema_2 = 0.0;
   if(!ComputeEMAFromSeries(lwma_vals, count, IndicatorCrsMAPrd1, ema_1, ema_2))
      return false;

   double lwma_1 = lwma_vals[0];
   double lwma_2 = lwma_vals[1];
   return lwma_1 < ema_1 && lwma_2 >= ema_2;
}}

double MinStopDistancePrice()
{{
   int stops_level = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = 0.00001;
   return MathMax(point, stops_level * point);
}}

bool PlaceLongEntry(const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double min_dist = MinStopDistancePrice();
   if(ask > 0.0 && entry_price <= ask + min_dist)
      return false;
   return trade.BuyStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
}}

bool PlaceShortEntry(const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double min_dist = MinStopDistancePrice();
   if(bid > 0.0 && entry_price >= bid - min_dist)
      return false;
   return trade.SellStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
}}

void ManageTrailingStops()
{{
   double atr45_1 = 0.0, atr100_1 = 0.0;
   if(!CopyValue(g_atr2_handle, 0, 1, atr45_1) || !CopyValue(g_atr4_handle, 0, 1, atr100_1))
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

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);

      if(type == POSITION_TYPE_BUY)
      {{
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if((bid - open_price) < (TrailingActCef1 * atr45_1))
            continue;
         double new_sl = bid - TrailingStop1;
         if(sl == 0.0 || new_sl > sl)
            trade.PositionModify(_Symbol, new_sl, tp);
      }}
      else if(type == POSITION_TYPE_SELL)
      {{
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double new_sl = ask + (TrailingStopCoef1 * atr100_1);
         if(sl == 0.0 || new_sl < sl)
            trade.PositionModify(_Symbol, new_sl, tp);
      }}
   }}
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ao_handle = iAO(_Symbol, InpTimeframe);
   g_lwma_handle = iMA(_Symbol, InpTimeframe, LWMAPeriod1, 0, MODE_LWMA, PRICE_CLOSE);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATR1Period);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATR2Period);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATR3Period);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATR4Period);
   if(g_ao_handle == INVALID_HANDLE || g_lwma_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE || g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ao_handle != INVALID_HANDLE) IndicatorRelease(g_ao_handle);
   if(g_lwma_handle != INVALID_HANDLE) IndicatorRelease(g_lwma_handle);
   if(g_atr1_handle != INVALID_HANDLE) IndicatorRelease(g_atr1_handle);
   if(g_atr2_handle != INVALID_HANDLE) IndicatorRelease(g_atr2_handle);
   if(g_atr3_handle != INVALID_HANDLE) IndicatorRelease(g_atr3_handle);
   if(g_atr4_handle != INVALID_HANDLE) IndicatorRelease(g_atr4_handle);
}}

void OnTick()
{{
   ManageTrailingStops();

   datetime now = TimeCurrent();
   if(IsFridayForceFlatTime(now))
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}

   if(!InBrokerTradableWindow(now))
      CancelManagedOrders();

   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(IsFridayForceFlatTime(bar_time))
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

   CancelExpiredOrders(bar_time);
    if(!InBrokerTradableWindow(bar_time))
      return;
   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr19_1 = 0.0, atr14_1 = 0.0;
   if(!CopyValue(g_atr1_handle, 0, 1, atr19_1) || !CopyValue(g_atr3_handle, 0, 1, atr14_1))
      return;

   bool long_signal = LongSignal();
   bool short_signal = ShortSignal();
   double highest_1 = HighestClose(HighestPeriod, 1);
   double lowest_1 = LowestClose(LowestPeriod, 1);
   datetime expiry = bar_time + PeriodSeconds(InpTimeframe);

   if(long_signal && !short_signal)
   {{
      double sl = highest_1 - StopLossCoef1 * atr19_1;
      double tp = highest_1 + ProfitTargetCoef1 * atr19_1;
      if(PlaceLongEntry(highest_1, sl, tp, expiry))
         g_long_expiry = expiry;
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double sl = lowest_1 + StopLossCoef2 * atr14_1;
      double tp = lowest_1 - ProfitTargetCoef2 * atr19_1;
      if(PlaceShortEntry(lowest_1, sl, tp, expiry))
         g_short_expiry = expiry;
   }}
}}
"""
