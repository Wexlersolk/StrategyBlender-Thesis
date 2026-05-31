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

def render_sqx_xau_short_keltner_breakout_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    direction_mode = str(payload.get("direction_mode", "short_only"))
    short_keltner_band = str(payload.get("short_keltner_band", "middle")).strip().lower() or "middle"
    allow_long = "true" if direction_mode != "short_only" else "false"
    allow_short = "true" if direction_mode != "long_only" else "false"
    keltner_expr = {
        "upper": "kc_mid + 1.5 * atr_stop_2",
        "lower": "kc_mid - 1.5 * atr_stop_2",
    }.get(short_keltner_band, "kc_mid")

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
input int IndicatorMAPeriod1 = {parse_int(params.get("IndicatorMAPeriod1", 59), 59)};
input int StochasticKPeriod1 = {parse_int(params.get("StochasticKPeriod1", 14), 14)};
input int StochasticDPeriod1 = {parse_int(params.get("StochasticDPeriod1", 7), 7)};
input int StochasticSlowing1 = {parse_int(params.get("StochasticSlowing1", 3), 3)};
input int KCerPeriod1 = {parse_int(params.get("KCerPeriod1", 20), 20)};
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 370), 370)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 370), 370)};
input int ATRTargetPeriod1 = {parse_int(params.get("ATRTargetPeriod1", 19), 19)};
input int ATRStopPeriod1 = {parse_int(params.get("ATRStopPeriod1", 14), 14)};
input int ATRTargetPeriod2 = {parse_int(params.get("ATRTargetPeriod2", 14), 14)};
input int ATRStopPeriod2 = {parse_int(params.get("ATRStopPeriod2", 14), 14)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 3.5), 3.5)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.0), 2.0)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.1), 3.1)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.4), 2.4)};
input int LongExpiryBars = {parse_int(params.get("LongExpiryBars", 18), 18)};
input int ShortExpiryBars = {parse_int(params.get("ShortExpiryBars", 1), 1)};
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
int g_stoch_handle = INVALID_HANDLE;
int g_kc_mid_handle = INVALID_HANDLE;
int g_atr_target_1_handle = INVALID_HANDLE;
int g_atr_stop_1_handle = INVALID_HANDLE;
int g_atr_target_2_handle = INVALID_HANDLE;
int g_atr_stop_2_handle = INVALID_HANDLE;

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

double WMAFromStochSignal(const int shift, const int period)
{{
   double values[];
   ArraySetAsSeries(values, true);
   if(CopyBuffer(g_stoch_handle, 1, shift, period, values) < period)
      return EMPTY_VALUE;
   double numerator = 0.0;
   double denominator = 0.0;
   for(int i = 0; i < period; ++i)
   {{
      double weight = (double)(period - i);
      numerator += values[i] * weight;
      denominator += weight;
   }}
   return denominator == 0.0 ? EMPTY_VALUE : numerator / denominator;
}}

bool LongSignal()
{{
   if(!InpAllowLong)
      return false;
   double stoch_signal = 0.0;
   if(!CopyValue(g_stoch_handle, 1, 3, stoch_signal))
      return false;
   double stoch_ma = WMAFromStochSignal(3, IndicatorMAPeriod1);
   if(stoch_ma == EMPTY_VALUE)
      return false;
   return NormalizeDouble(stoch_signal, 6) > NormalizeDouble(stoch_ma, 6);
}}

bool ShortSignal()
{{
   if(!InpAllowShort)
      return false;
   double kc_mid_3 = 0.0, kc_mid_4 = 0.0, kc_mid_5 = 0.0;
   if(!CopyValue(g_kc_mid_handle, 0, 3, kc_mid_3) || !CopyValue(g_kc_mid_handle, 0, 4, kc_mid_4) || !CopyValue(g_kc_mid_handle, 0, 5, kc_mid_5))
      return false;
   double atr_stop_2_3 = 0.0, atr_stop_2_4 = 0.0, atr_stop_2_5 = 0.0;
   if(!CopyValue(g_atr_stop_2_handle, 0, 3, atr_stop_2_3) || !CopyValue(g_atr_stop_2_handle, 0, 4, atr_stop_2_4) || !CopyValue(g_atr_stop_2_handle, 0, 5, atr_stop_2_5))
      return false;
   double band_3 = {keltner_expr.replace("kc_mid", "kc_mid_3").replace("atr_stop_2", "atr_stop_2_3")};
   double band_4 = {keltner_expr.replace("kc_mid", "kc_mid_4").replace("atr_stop_2", "atr_stop_2_4")};
   double band_5 = {keltner_expr.replace("kc_mid", "kc_mid_5").replace("atr_stop_2", "atr_stop_2_5")};
   return NormalizeDouble(band_3, 6) > NormalizeDouble(band_4, 6) && NormalizeDouble(band_4, 6) > NormalizeDouble(band_5, 6);
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_stoch_handle = iStochastic(_Symbol, InpTimeframe, StochasticKPeriod1, StochasticDPeriod1, StochasticSlowing1, MODE_SMA, STO_LOWHIGH);
   g_kc_mid_handle = iMA(_Symbol, InpTimeframe, KCerPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_target_1_handle = iATR(_Symbol, InpTimeframe, ATRTargetPeriod1);
   g_atr_stop_1_handle = iATR(_Symbol, InpTimeframe, ATRStopPeriod1);
   g_atr_target_2_handle = iATR(_Symbol, InpTimeframe, ATRTargetPeriod2);
   g_atr_stop_2_handle = iATR(_Symbol, InpTimeframe, ATRStopPeriod2);
   if(g_stoch_handle == INVALID_HANDLE || g_kc_mid_handle == INVALID_HANDLE || g_atr_target_1_handle == INVALID_HANDLE || g_atr_stop_1_handle == INVALID_HANDLE || g_atr_target_2_handle == INVALID_HANDLE || g_atr_stop_2_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_stoch_handle != INVALID_HANDLE) IndicatorRelease(g_stoch_handle);
   if(g_kc_mid_handle != INVALID_HANDLE) IndicatorRelease(g_kc_mid_handle);
   if(g_atr_target_1_handle != INVALID_HANDLE) IndicatorRelease(g_atr_target_1_handle);
   if(g_atr_stop_1_handle != INVALID_HANDLE) IndicatorRelease(g_atr_stop_1_handle);
   if(g_atr_target_2_handle != INVALID_HANDLE) IndicatorRelease(g_atr_target_2_handle);
   if(g_atr_stop_2_handle != INVALID_HANDLE) IndicatorRelease(g_atr_stop_2_handle);
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

   double atr_target_1 = 0.0, atr_stop_1 = 0.0, atr_target_2 = 0.0, atr_stop_2 = 0.0;
   if(!CopyValue(g_atr_target_1_handle, 0, 1, atr_target_1) || !CopyValue(g_atr_stop_1_handle, 0, 1, atr_stop_1) || !CopyValue(g_atr_target_2_handle, 0, 1, atr_target_2) || !CopyValue(g_atr_stop_2_handle, 0, 1, atr_stop_2))
      return;

   double highest_1 = HighestClose(HighestPeriod, 2);
   double lowest_1 = LowestClose(LowestPeriod, 2);
   datetime long_expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
   datetime short_expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;

   if(LongSignal() && !ShortSignal())
   {{
      double sl = highest_1 - StopLossCoef1 * atr_stop_1;
      double tp = highest_1 + ProfitTargetCoef1 * atr_target_1;
      if(trade.BuyStop(InpLots, highest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, long_expiry, "{strategy_id}_long"))
         g_long_expiry = long_expiry;
      return;
   }}

   if(ShortSignal() && !LongSignal())
   {{
      double sl = lowest_1 + StopLossCoef2 * atr_stop_2;
      double tp = lowest_1 - ProfitTargetCoef2 * atr_target_2;
      if(trade.SellStop(InpLots, lowest_1, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, short_expiry, "{strategy_id}_short"))
         g_short_expiry = short_expiry;
   }}
}}
"""
