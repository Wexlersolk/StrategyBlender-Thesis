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

def render_sqx_batch_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = str(payload.get("symbol", "XAUUSD"))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    
    defaults = settings.symbol_execution_defaults(symbol)
    friday_flat_hhmm = str(defaults.get("force_flat_hhmm", "21:00"))
    friday_flat_hour = parse_int(friday_flat_hhmm[:2], 21)
    friday_flat_minute = parse_int(friday_flat_hhmm[3:], 0)
    
    signal_from, signal_to = signal_window_params(
        symbol,
        params,
        default_from="00:00",
        default_to="23:59",
    )
    
    long_mode = str(payload.get("long_signal_mode", "cross_above")).strip().lower()
    short_mode = str(payload.get("short_signal_mode", "cross_below")).strip().lower()

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(symbol, params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.5), 2.5)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 3.5), 3.5)};
input double TrailingActCef1 = {parse_float(params.get("TrailingActCef1", 1.5), 1.5)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 150.0), 150.0)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.5), 2.5)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.5), 3.5)};
input double TrailingStopCoef1 = {parse_float(params.get("TrailingStopCoef1", 1.0), 1.0)};
input int IndicatorCrsMAPrd1 = {parse_int(params.get("IndicatorCrsMAPrd1", 50), 50)};
input int IndicatorCrsMAPrd2 = {parse_int(params.get("IndicatorCrsMAPrd2", 50), 50)};
input int ATR1Period = {parse_int(params.get("ATR1_period", 14), 14)};
input int ATR2Period = {parse_int(params.get("ATR2_period", 20), 20)};
input int ATR3Period = {parse_int(params.get("ATR3_period", 14), 14)};
input int ATR4Period = {parse_int(params.get("ATR4_period", 50), 50)};
input int HighestPeriod = {parse_int(params.get("Highest_period", 20), 20)};
input int LowestPeriod = {parse_int(params.get("Lowest_period", 20), 20)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 0)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 23)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 59)};
input int FridayFlatHour = {friday_flat_hour};
input int FridayFlatMinute = {friday_flat_minute};

datetime g_last_bar_time = 0;
datetime g_last_trade_bar = 0; // Tracks the bar time of the last opened position to prevent multiple trades per bar
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_main_handle = INVALID_HANDLE;
int g_sig_handle = INVALID_HANDLE;
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
      if(type == ORDER_TYPE_BUY_STOP && comment == "batch_long" && g_long_expiry != 0 && bar_time >= g_long_expiry)
         trade.OrderDelete(ticket);
      if(type == ORDER_TYPE_SELL_STOP && comment == "batch_short" && g_short_expiry != 0 && bar_time >= g_short_expiry)
         trade.OrderDelete(ticket);
   }}
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

bool PlaceLongStopOrMarket(const double entry_price, const double sl, const double tp)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return false;
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;
   double min_distance = MathMax((double)stops_level * point, point);
   double adjusted_entry = MathMax(entry_price, ask + min_distance);
   return trade.BuyStop(InpLots, NormalizeDouble(adjusted_entry, _Digits), _Symbol, sl, tp, ORDER_TIME_GTC, 0, "batch_long");
}}

bool PlaceShortStopOrMarket(const double entry_price, const double sl, const double tp)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;
   double min_distance = MathMax((double)stops_level * point, point);
   double adjusted_entry = MathMin(entry_price, bid - min_distance);
   return trade.SellStop(InpLots, NormalizeDouble(adjusted_entry, _Digits), _Symbol, sl, tp, ORDER_TIME_GTC, 0, "batch_short");
}}

int OnInit()
{{
   g_main_handle = iMA(_Symbol, InpTimeframe, IndicatorCrsMAPrd1, 0, MODE_EMA, PRICE_CLOSE);
   g_sig_handle = iMA(_Symbol, InpTimeframe, IndicatorCrsMAPrd2, 0, MODE_SMA, g_main_handle);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATR1Period);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATR2Period);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATR3Period);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATR4Period);
   
   if(g_main_handle == INVALID_HANDLE || g_sig_handle == INVALID_HANDLE ||
      g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE ||
      g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
   {{
      Print("Error creating handles");
      return INIT_FAILED;
   }}
   
   trade.SetExpertMagicNumber(InpMagicNumber);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(g_main_handle);
   IndicatorRelease(g_sig_handle);
   IndicatorRelease(g_atr1_handle);
   IndicatorRelease(g_atr2_handle);
   IndicatorRelease(g_atr3_handle);
   IndicatorRelease(g_atr4_handle);
}}

void OnTick()
{{
   datetime now = TimeCurrent();
   if(IsFridayForceFlatTime(now))
   {{
      if(HasOpenPosition()) CloseManagedPositions();
      if(HasPendingOrders()) CancelManagedOrders();
      return;
   }}

   if(HasOpenPosition())
   {{
      // Record that we have a position open for the current bar to prevent re-entry if it closes early
      g_last_trade_bar = iTime(_Symbol, InpTimeframe, 0);

      // Trailing stop
      for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
      {{
         ulong ticket = PositionGetTicket(idx);
         if(!PositionSelectByTicket(ticket)) continue;
         if(PositionGetString(POSITION_SYMBOL) != _Symbol || (int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
         
         double atr3, atr4;
         if(!CopyValue(g_atr3_handle, 0, 1, atr3)) continue;
         if(!CopyValue(g_atr4_handle, 0, 1, atr4)) continue;
         
         double pos_open = PositionGetDouble(POSITION_PRICE_OPEN);
         double pos_sl = PositionGetDouble(POSITION_SL);
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         
         if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
         {{
            double activation = pos_open + TrailingActCef1 * atr3;
            if(bid >= activation)
            {{
               double new_sl = bid - TrailingStop1 * 0.001;
               if(new_sl > pos_sl + 0.0001 || pos_sl == 0)
                  trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
            }}
         }}
         else if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
         {{
            double new_sl = ask + TrailingStopCoef1 * atr4;
            if(new_sl < pos_sl - 0.0001 || pos_sl == 0)
               trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
         }}
      }}
   }}

   if(!IsNewBar()) return;
   
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   CancelExpiredOrders(bar_time);
   
   // HARD TRADE LIMIT: Max 1 trade per bar.
   // This prevents "loss loops" where a position is opened and stopped out multiple times within a single H4 bar.
   // Synchronization: The native engine inherently operates on bar-closes, so this brings MT5 behavior closer to the discovery engine.
   if(HasOpenPosition() || bar_time <= g_last_trade_bar) return;
   if(HasPendingOrders()) return;
   if(!InTimeWindow(bar_time)) return;

   double main0, main1, sig0, sig1;
   if(!CopyValue(g_main_handle, 0, 1, main0)) return;
   if(!CopyValue(g_main_handle, 0, 2, main1)) return;
   if(!CopyValue(g_sig_handle, 0, 1, sig0)) return;
   if(!CopyValue(g_sig_handle, 0, 2, sig1)) return;

   bool long_signal = false;
   bool short_signal = false;

   if("{long_mode}" == "cross_above")
      long_signal = (main1 <= sig1 && main0 > sig0);
   else if("{long_mode}" == "rising")
      long_signal = (main0 > main1);
   else
      long_signal = (main0 > sig0);

   if("{short_mode}" == "cross_below")
      short_signal = (main1 >= sig1 && main0 < sig0);
   else if("{short_mode}" == "falling")
      short_signal = (main0 < main1);
   else
      short_signal = (main0 < sig0);

   if({str(payload.get("debug_log", False)).lower()})
   {{
      double atr1, atr2, atr3, atr4;
      CopyValue(g_atr1_handle, 0, 1, atr1);
      CopyValue(g_atr2_handle, 0, 1, atr2);
      CopyValue(g_atr3_handle, 0, 1, atr3);
      CopyValue(g_atr4_handle, 0, 1, atr4);
      PrintFormat("[DEBUG_TRACE] %s | main0: %.5f, sig0: %.5f, main1: %.5f, sig1: %.5f, atr1: %.5f, atr2: %.5f, atr3: %.5f, atr4: %.5f, long: %d, short: %d", 
                  TimeToString(bar_time), main0, sig0, main1, sig1, atr1, atr2, atr3, atr4, long_signal, short_signal);
   }}

   if(long_signal && !short_signal)
   {{
      double highest = HighestHigh(HighestPeriod, 1);
      double atr1, atr2;
      if(CopyValue(g_atr1_handle, 0, 1, atr1) && CopyValue(g_atr2_handle, 0, 1, atr2))
      {{
         double price = highest;
         double sl = price - StopLossCoef1 * atr1;
         double tp = price + ProfitTargetCoef1 * atr2;
         if(PlaceLongStopOrMarket(price, sl, tp))
            g_long_expiry = bar_time + PeriodSeconds(InpTimeframe) * 5;
      }}
   }}
   else if(short_signal && !long_signal)
   {{
      double lowest = LowestLow(LowestPeriod, 1);
      double atr1, atr2;
      if(CopyValue(g_atr1_handle, 0, 1, atr1) && CopyValue(g_atr2_handle, 0, 1, atr2))
      {{
         double price = lowest;
         double sl = lowest + StopLossCoef2 * atr1;
         double tp = lowest - ProfitTargetCoef2 * atr2;
         if(PlaceShortStopOrMarket(price, sl, tp))
            g_short_expiry = bar_time + PeriodSeconds(InpTimeframe) * 5;
      }}
   }}
}}
"""
