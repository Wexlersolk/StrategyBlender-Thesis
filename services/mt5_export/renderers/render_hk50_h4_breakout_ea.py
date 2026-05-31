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

def render_hk50_h4_breakout_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = "HK50.cash"
    mql_tf = "PERIOD_H4"
    
    long_signal_mode = str(payload.get("long_signal_mode", "wpr_rising")).strip().lower()
    short_signal_mode = str(payload.get("short_signal_mode", "wpr_rising")).strip().lower()

    signal_from, signal_to = signal_window_params(
        symbol,
        params,
        default_from="00:00",
        default_to="23:59",
    )
    
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(symbol, params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 1.8), 1.8)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 3.2), 3.2)};
input double TrailingActCef1 = {parse_float(params.get("TrailingActCef1", 1.5), 1.5)};
input double TrailingStopCoef1 = {parse_float(params.get("TrailingStopCoef1", 1.0), 1.0)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 1.8), 1.8)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.2), 3.2)};
input int ATRPeriod = {parse_int(params.get("ATR_period", 14), 14)};
input int WPRPeriod = {parse_int(params.get("WPR_period", 20), 20)};
input int MomentumPeriod = {parse_int(params.get("Momentum_period", 80), 80)};
input int QQERsiPeriod = {parse_int(params.get("QQE_rsi_period", 50), 50)};
input int QQESmooth = {parse_int(params.get("QQE_smooth", 5), 5)};
input int HighestPeriod = {parse_int(params.get("Highest_period", 10), 10)};
input int LowestPeriod = {parse_int(params.get("Lowest_period", 10), 10)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 0)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 23)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 59)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_atr_handle = INVALID_HANDLE;
int g_wpr_handle = INVALID_HANDLE;
int g_mom_handle = INVALID_HANDLE;
int g_rsi_handle = INVALID_HANDLE;
int g_qqe_main_handle = INVALID_HANDLE;
int g_qqe_sig_handle = INVALID_HANDLE;
int g_sma_20_handle = INVALID_HANDLE;

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

bool HasOpenPosition()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol || (int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      return true;
   }}
   return false;
}}

bool HasPendingOrders()
{{
   for(int idx = OrdersTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = OrderGetTicket(idx);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol || (int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber) continue;
      return true;
   }}
   return false;
}}

void CancelManagedOrders()
{{
   for(int idx = OrdersTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = OrderGetTicket(idx);
      if(ticket == 0 || !OrderSelect(ticket)) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol || (int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber) continue;
      trade.OrderDelete(ticket);
   }}
}}

double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iHigh(_Symbol, InpTimeframe, shift);
      if(x != 0.0) value = MathMax(value, x);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}

double LowestLow(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iLow(_Symbol, InpTimeframe, shift);
      if(x != 0.0) value = MathMin(value, x);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   g_wpr_handle = iWPR(_Symbol, InpTimeframe, WPRPeriod);
   g_mom_handle = iMomentum(_Symbol, InpTimeframe, MomentumPeriod, PRICE_CLOSE);
   g_rsi_handle = iRSI(_Symbol, InpTimeframe, QQERsiPeriod, PRICE_CLOSE);
   g_qqe_main_handle = iMA(_Symbol, InpTimeframe, QQESmooth, 0, MODE_EMA, g_rsi_handle);
   g_qqe_sig_handle = iMA(_Symbol, InpTimeframe, QQESmooth, 0, MODE_EMA, g_qqe_main_handle);
   g_sma_20_handle = iMA(_Symbol, InpTimeframe, 20, 0, MODE_SMA, PRICE_CLOSE);
   
   if(g_atr_handle == INVALID_HANDLE || g_wpr_handle == INVALID_HANDLE || g_mom_handle == INVALID_HANDLE || g_rsi_handle == INVALID_HANDLE || g_qqe_main_handle == INVALID_HANDLE || g_qqe_sig_handle == INVALID_HANDLE || g_sma_20_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(g_atr_handle);
   IndicatorRelease(g_wpr_handle);
   IndicatorRelease(g_mom_handle);
   IndicatorRelease(g_rsi_handle);
   IndicatorRelease(g_qqe_main_handle);
   IndicatorRelease(g_qqe_sig_handle);
   IndicatorRelease(g_sma_20_handle);
}}

void OnTick()
{{
   if(HasOpenPosition())
   {{
      for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
      {{
         ulong ticket = PositionGetTicket(idx);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || (int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
         
         double atr;
         if(!CopyValue(g_atr_handle, 0, 1, atr)) continue;
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl = PositionGetDouble(POSITION_SL);
         
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
         {{
            double activation = open_price + TrailingActCef1 * atr;
            if(bid >= activation)
            {{
               double new_sl = bid - TrailingStopCoef1 * atr;
               if(new_sl > sl || sl == 0) trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }}
         }}
         else if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
         {{
            double activation = open_price - TrailingActCef1 * atr;
            if(ask <= activation)
            {{
               double new_sl = ask + TrailingStopCoef1 * atr;
               if(new_sl < sl || sl == 0) trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }}
         }}
      }}
   }}

   if(!IsNewBar()) return;
   
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(HasPendingOrders()) CancelManagedOrders();
   if(!InTimeWindow(bar_time)) return;
   if(HasOpenPosition()) return;

   bool long_signal = false;
   bool short_signal = false;

   if("{long_signal_mode}" == "wpr_rising")
   {{
      double wpr0, wpr1;
      if(CopyValue(g_wpr_handle, 0, 1, wpr0) && CopyValue(g_wpr_handle, 0, 2, wpr1))
         long_signal = (wpr0 > wpr1);
   }}
   else if("{long_signal_mode}" == "qqe_bullish")
   {{
      double qqe, sig;
      if(CopyValue(g_qqe_main_handle, 0, 1, qqe) && CopyValue(g_qqe_sig_handle, 0, 1, sig))
         long_signal = (qqe > sig);
   }}
   else if("{long_signal_mode}" == "momentum_rising")
   {{
      double mom0, mom1;
      if(CopyValue(g_mom_handle, 0, 1, mom0) && CopyValue(g_mom_handle, 0, 2, mom1))
         long_signal = (mom0 > mom1);
   }}
   else if("{long_signal_mode}" == "hour_morning")
   {{
      MqlDateTime dt;
      TimeToStruct(bar_time, dt);
      long_signal = (dt.hour < 11);
   }}

   if("{short_signal_mode}" == "wpr_rising")
   {{
      double wpr0, wpr1;
      if(CopyValue(g_wpr_handle, 0, 1, wpr0) && CopyValue(g_wpr_handle, 0, 2, wpr1))
         short_signal = (wpr0 > wpr1);
   }}
   else if("{short_signal_mode}" == "qqe_bearish")
   {{
      double qqe, sig;
      if(CopyValue(g_qqe_main_handle, 0, 1, qqe) && CopyValue(g_qqe_sig_handle, 0, 1, sig))
         short_signal = (qqe < sig);
   }}
   else if("{short_signal_mode}" == "momentum_falling")
   {{
      double mom0, mom1;
      if(CopyValue(g_mom_handle, 0, 1, mom0) && CopyValue(g_mom_handle, 0, 2, mom1))
         short_signal = (mom0 < mom1);
   }}
   else if("{short_signal_mode}" == "sma_falling")
   {{
      double sma0, sma1;
      if(CopyValue(g_sma_20_handle, 0, 1, sma0) && CopyValue(g_sma_20_handle, 0, 2, sma1))
         short_signal = (sma0 < sma1);
   }}

   double atr;
   if(!CopyValue(g_atr_handle, 0, 1, atr)) return;

   if(long_signal && !short_signal)
   {{
      double entry = HighestHigh(HighestPeriod, 1);
      double sl = entry - StopLossCoef1 * atr;
      double tp = entry + ProfitTargetCoef1 * atr;
      trade.BuyStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "hk50_h4_long");
   }}
   else if(short_signal && !long_signal)
   {{
      double entry = LowestLow(LowestPeriod, 1);
      double sl = entry + StopLossCoef2 * atr;
      double tp = entry - ProfitTargetCoef2 * atr;
      trade.SellStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "hk50_h4_short");
   }}
}}
"""
