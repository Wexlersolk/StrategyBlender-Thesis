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

def render_sqx_us100_nasdaq_smma_keltner_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    signal_from, signal_to = signal_window_params(
        payload.get("symbol"),
        params,
        default_from="00:00",
        default_to="23:59",
    )
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = {normalized_export_lots(payload.get("symbol"), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int SMMAPeriod1 = {parse_int(params.get("SMMAPeriod1", 12), 12)};
input int EWMAPeriod1 = {parse_int(params.get("EWMAPeriod1", 20), 20)};
input int ROCPeriod1 = {parse_int(params.get("ROCPeriod1", 12), 12)};
input double ROCThreshold1 = {parse_float(params.get("ROCThreshold1", 50.3), 50.3)};
input int KCFastPeriod1 = {parse_int(params.get("KCFastPeriod1", 20), 20)};
input double KCFastMult1 = {parse_float(params.get("KCFastMult1", 2.5), 2.5)};
input int KCSlowPeriod1 = {parse_int(params.get("KCSlowPeriod1", 73), 73)};
input double KCSlowMult1 = {parse_float(params.get("KCSlowMult1", 2.4), 2.4)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 50), 50)};
input int ATRPeriod2 = {parse_int(params.get("ATRPeriod2", 19), 19)};
input int ATRPeriod3 = {parse_int(params.get("ATRPeriod3", 14), 14)};
input int ATRPeriod4 = {parse_int(params.get("ATRPeriod4", 65), 65)};
input double PriceEntryMult1 = {parse_float(params.get("PriceEntryMult1", 2.0), 2.0)};
input int ExitAfterBars1 = {parse_int(params.get("ExitAfterBars1", 12), 12)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 6.0), 6.0)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 2.2), 2.2)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 5.6), 5.6)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 2.3), 2.3)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 360.0), 360.0)};
input double TrailingActCef1 = {parse_float(params.get("TrailingActCef1", 3.9), 3.9)};
input int LongExpiryBars = 4;
input int ShortExpiryBars = 4;

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 0)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 23)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 59)};
input int FridayExitHour = {parse_int(str(params.get("FridayExitTime", "22:38"))[:2], 22)};
input int FridayExitMinute = {parse_int(str(params.get("FridayExitTime", "22:38"))[3:], 38)};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;
int g_smma_low_handle = INVALID_HANDLE;
int g_smma_high_handle = INVALID_HANDLE;
int g_ema_close_handle = INVALID_HANDLE;
int g_kc_fast_ema_handle = INVALID_HANDLE;
int g_kc_slow_ema_handle = INVALID_HANDLE;
int g_kc_fast_atr_handle = INVALID_HANDLE;
int g_kc_slow_atr_handle = INVALID_HANDLE;
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
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_LIMIT || type == ORDER_TYPE_SELL_STOP)
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
      if(type == ORDER_TYPE_BUY_LIMIT && comment == "{strategy_id}_long" && g_long_expiry != 0 && bar_time >= g_long_expiry)
         trade.OrderDelete(ticket);
      if(type == ORDER_TYPE_SELL_STOP && comment == "{strategy_id}_short" && g_short_expiry != 0 && bar_time >= g_short_expiry)
         trade.OrderDelete(ticket);
   }}
}}

void ManageTimedLongExit(const datetime bar_time)
{{
   if(ExitAfterBars1 <= 0)
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
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_BUY)
         continue;
      datetime entry_time = (datetime)PositionGetInteger(POSITION_TIME);
      if(entry_time == 0)
         continue;
      int held_bars = (int)((bar_time - entry_time) / PeriodSeconds(InpTimeframe));
      if(held_bars >= ExitAfterBars1)
         trade.PositionClose(ticket);
   }}
}}

void ManageTrailingStops()
{{
   double atr4 = 0.0;
   if(!CopyValue(g_atr4_handle, 0, 1, atr4))
      return;
   double activation = TrailingActCef1 * atr4;
   double trail_dist = TrailingStop1;
   if(activation <= 0.0 || trail_dist <= 0.0)
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
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_SELL)
         continue;
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double profit_distance = open_price - ask;
      if(profit_distance < activation)
         continue;
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double new_sl = ask + trail_dist;
      if(sl == 0.0 || new_sl < sl)
         trade.PositionModify(ticket, new_sl, tp);
   }}
}}

double CloseRef(const int shift)
{{
   return iClose(_Symbol, InpTimeframe, shift);
}}

double RocValue(const int shift)
{{
   double close_now = CloseRef(shift);
   double close_then = CloseRef(shift + ROCPeriod1);
   if(close_now == 0.0 || close_then == 0.0)
      return 50.0;
   return ((close_now / close_then) - 1.0) * 100.0 + 50.0;
}}

double KeltnerLowerFast(const int shift)
{{
   double mid = 0.0, atr = 0.0;
   if(!CopyValue(g_kc_fast_ema_handle, 0, shift, mid) || !CopyValue(g_kc_fast_atr_handle, 0, shift, atr))
      return 0.0;
   return mid - KCFastMult1 * atr;
}}

double KeltnerLowerSlow(const int shift)
{{
   double mid = 0.0, atr = 0.0;
   if(!CopyValue(g_kc_slow_ema_handle, 0, shift, mid) || !CopyValue(g_kc_slow_atr_handle, 0, shift, atr))
      return 0.0;
   return mid - KCSlowMult1 * atr;
}}

bool LongSignal()
{{
   double smma_low = 0.0, ema_close = 0.0;
   if(!CopyValue(g_smma_low_handle, 0, 1, smma_low) || !CopyValue(g_ema_close_handle, 0, 1, ema_close))
      return false;
   return smma_low > ema_close;
}}

bool ShortSignal()
{{
   double smma_high = 0.0, ema_close = 0.0;
   if(!CopyValue(g_smma_high_handle, 0, 1, smma_high) || !CopyValue(g_ema_close_handle, 0, 1, ema_close))
      return false;
   return smma_high < ema_close;
}}

bool ShortExitSignal()
{{
   double close_1 = CloseRef(1);
   double close_2 = CloseRef(2);
   if(close_1 == 0.0 || close_2 == 0.0)
      return false;
   return (close_1 < close_2) && (RocValue(1) > ROCThreshold1);
}}

bool PlaceLongEntry(const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(entry_price >= ask)
      return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
   return trade.BuyLimit(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
}}

bool PlaceShortEntry(const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(entry_price >= bid)
      return trade.Sell(InpLots, _Symbol, bid, sl, tp, "{strategy_id}_short");
   return trade.SellStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_smma_low_handle = iMA(_Symbol, InpTimeframe, SMMAPeriod1, 0, MODE_SMMA, PRICE_LOW);
   g_smma_high_handle = iMA(_Symbol, InpTimeframe, SMMAPeriod1, 0, MODE_SMMA, PRICE_HIGH);
   g_ema_close_handle = iMA(_Symbol, InpTimeframe, EWMAPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_kc_fast_ema_handle = iMA(_Symbol, InpTimeframe, KCFastPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_kc_slow_ema_handle = iMA(_Symbol, InpTimeframe, KCSlowPeriod1, 0, MODE_EMA, PRICE_CLOSE);
   g_kc_fast_atr_handle = iATR(_Symbol, InpTimeframe, KCFastPeriod1);
   g_kc_slow_atr_handle = iATR(_Symbol, InpTimeframe, KCSlowPeriod1);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATRPeriod1);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATRPeriod2);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATRPeriod3);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATRPeriod4);
   if(g_smma_low_handle == INVALID_HANDLE || g_smma_high_handle == INVALID_HANDLE || g_ema_close_handle == INVALID_HANDLE || g_kc_fast_ema_handle == INVALID_HANDLE || g_kc_slow_ema_handle == INVALID_HANDLE || g_kc_fast_atr_handle == INVALID_HANDLE || g_kc_slow_atr_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE || g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_smma_low_handle != INVALID_HANDLE) IndicatorRelease(g_smma_low_handle);
   if(g_smma_high_handle != INVALID_HANDLE) IndicatorRelease(g_smma_high_handle);
   if(g_ema_close_handle != INVALID_HANDLE) IndicatorRelease(g_ema_close_handle);
   if(g_kc_fast_ema_handle != INVALID_HANDLE) IndicatorRelease(g_kc_fast_ema_handle);
   if(g_kc_slow_ema_handle != INVALID_HANDLE) IndicatorRelease(g_kc_slow_ema_handle);
   if(g_kc_fast_atr_handle != INVALID_HANDLE) IndicatorRelease(g_kc_fast_atr_handle);
   if(g_kc_slow_atr_handle != INVALID_HANDLE) IndicatorRelease(g_kc_slow_atr_handle);
   if(g_atr1_handle != INVALID_HANDLE) IndicatorRelease(g_atr1_handle);
   if(g_atr2_handle != INVALID_HANDLE) IndicatorRelease(g_atr2_handle);
   if(g_atr3_handle != INVALID_HANDLE) IndicatorRelease(g_atr3_handle);
   if(g_atr4_handle != INVALID_HANDLE) IndicatorRelease(g_atr4_handle);
}}

void OnTick()
{{
   ManageTrailingStops();

   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(IsFridayExitTime(bar_time))
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

   if(ShortExitSignal())
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
         if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
            trade.PositionClose(ticket);
      }}
   }}

   ManageTimedLongExit(bar_time);
   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders())
      return;

   if(!InTimeWindow(bar_time))
      return;

   bool long_signal = LongSignal();
   bool short_signal = ShortSignal();
   double atr1 = 0.0, atr2 = 0.0, atr3 = 0.0;
   if(!CopyValue(g_atr1_handle, 0, 1, atr1) || !CopyValue(g_atr2_handle, 0, 1, atr2) || !CopyValue(g_atr3_handle, 0, 1, atr3))
      return;

   if(long_signal)
   {{
      double base = KeltnerLowerFast(1) + (PriceEntryMult1 * atr1);
      double sl = base - (StopLossCoef1 * atr3);
      double tp = base + (ProfitTargetCoef1 * atr2);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
      if(PlaceLongEntry(base, sl, tp, expiry))
         g_long_expiry = expiry;
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double base = KeltnerLowerSlow(1);
      double sl = base + (StopLossCoef2 * atr3);
      double tp = base - (ProfitTargetCoef2 * atr2);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;
      if(PlaceShortEntry(base, sl, tp, expiry))
         g_short_expiry = expiry;
   }}
}}
"""
