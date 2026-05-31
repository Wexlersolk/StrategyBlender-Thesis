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

def render_sqx_us100_nasdaq_ichi_keltner_ea(strategy_id: str, payload: dict[str, Any]) -> str:
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
input int SMMAPeriod1 = {parse_int(params.get("SMMAPeriod1", 40), 40)};
input int IchimokuTenkanPrd1 = {parse_int(params.get("IchimokuTenkanPrd1", 9), 9)};
input int IchimokuKijunPeriod1 = {parse_int(params.get("IchimokuKijunPeriod1", 26), 26)};
input int IchimokuSenkouPrd1 = {parse_int(params.get("IchimokuSenkouPrd1", 16), 16)};
input int KeltnerChannelPrd1 = {parse_int(params.get("KeltnerChannelPrd1", 70), 70)};
input double KeltnerMult1 = {parse_float(params.get("KeltnerMult1", 2.25), 2.25)};
input int LowestPeriod1 = {parse_int(params.get("LowestPeriod1", 25), 25)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 14), 14)};
input int ATRPeriod2 = {parse_int(params.get("ATRPeriod2", 20), 20)};
input int ATRPeriod3 = {parse_int(params.get("ATRPeriod3", 19), 19)};
input int ATRPeriod4 = {parse_int(params.get("ATRPeriod4", 50), 50)};
input double PriceEntryMult1 = {parse_float(params.get("PriceEntryMult1", 1.6), 1.6)};
input double PriceEntryMult2 = {parse_float(params.get("PriceEntryMult2", 1.2), 1.2)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 5.0), 5.0)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 1.9), 1.9)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.6), 3.6)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 1.5), 1.5)};
input int LongExpiryBars = 18;
input int ShortExpiryBars = 3;

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
int g_smma_close_handle = INVALID_HANDLE;
int g_ichi_handle = INVALID_HANDLE;
int g_kc_ema_handle = INVALID_HANDLE;
int g_kc_atr_handle = INVALID_HANDLE;
int g_atr1_handle = INVALID_HANDLE;
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

double KeltnerMid(const int shift)
{{
   double mid = 0.0;
   if(!CopyValue(g_kc_ema_handle, 0, shift, mid))
      return 0.0;
   return mid;
}}

bool LongSignal()
{{
   double low1 = iLow(_Symbol, InpTimeframe, 1);
   double close1 = iClose(_Symbol, InpTimeframe, 1);
   double smma1 = 0.0, kijun1 = 0.0;
   if(!CopyValue(g_smma_close_handle, 0, 1, smma1) || !CopyValue(g_ichi_handle, 1, 1, kijun1))
      return false;
   return low1 <= smma1 && close1 > kijun1;
}}

bool ShortSignal()
{{
   double high1 = iHigh(_Symbol, InpTimeframe, 1);
   double close1 = iClose(_Symbol, InpTimeframe, 1);
   double smma1 = 0.0, kijun1 = 0.0;
   if(!CopyValue(g_smma_close_handle, 0, 1, smma1) || !CopyValue(g_ichi_handle, 1, 1, kijun1))
      return false;
   return high1 >= smma1 && close1 < kijun1;
}}

bool LongExitSignal()
{{
   double kijun1 = 0.0, kc1 = 0.0;
   if(!CopyValue(g_ichi_handle, 1, 1, kijun1))
      return false;
   kc1 = KeltnerMid(1);
   return kijun1 < kc1;
}}

bool ShortExitSignal()
{{
   double close1 = iClose(_Symbol, InpTimeframe, 1);
   double smma1 = 0.0;
   if(!CopyValue(g_smma_close_handle, 0, 1, smma1))
      return false;
   return close1 > smma1;
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
   g_smma_close_handle = iMA(_Symbol, InpTimeframe, SMMAPeriod1, 0, MODE_SMMA, PRICE_CLOSE);
   g_ichi_handle = iIchimoku(_Symbol, InpTimeframe, IchimokuTenkanPrd1, IchimokuKijunPeriod1, IchimokuSenkouPrd1);
   g_kc_ema_handle = iMA(_Symbol, InpTimeframe, KeltnerChannelPrd1, 0, MODE_EMA, PRICE_CLOSE);
   g_kc_atr_handle = iATR(_Symbol, InpTimeframe, KeltnerChannelPrd1);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATRPeriod1);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATRPeriod3);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATRPeriod4);
   if(g_smma_close_handle == INVALID_HANDLE || g_ichi_handle == INVALID_HANDLE || g_kc_ema_handle == INVALID_HANDLE || g_kc_atr_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_smma_close_handle != INVALID_HANDLE) IndicatorRelease(g_smma_close_handle);
   if(g_ichi_handle != INVALID_HANDLE) IndicatorRelease(g_ichi_handle);
   if(g_kc_ema_handle != INVALID_HANDLE) IndicatorRelease(g_kc_ema_handle);
   if(g_kc_atr_handle != INVALID_HANDLE) IndicatorRelease(g_kc_atr_handle);
   if(g_atr1_handle != INVALID_HANDLE) IndicatorRelease(g_atr1_handle);
   if(g_atr3_handle != INVALID_HANDLE) IndicatorRelease(g_atr3_handle);
   if(g_atr4_handle != INVALID_HANDLE) IndicatorRelease(g_atr4_handle);
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

   if(LongExitSignal())
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
         if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
            trade.PositionClose(ticket);
      }}
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

   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders() || !InTimeWindow(bar_time))
      return;

   bool long_signal = LongSignal();
   bool short_signal = ShortSignal();
   double atr1 = 0.0, atr3 = 0.0, atr4 = 0.0, kijun1 = 0.0;
   if(!CopyValue(g_atr1_handle, 0, 1, atr1) || !CopyValue(g_atr3_handle, 0, 1, atr3) || !CopyValue(g_atr4_handle, 0, 1, atr4) || !CopyValue(g_ichi_handle, 1, 1, kijun1))
      return;

   if(long_signal)
   {{
      double base = LowestLow(LowestPeriod1, 1) + (PriceEntryMult1 * atr1);
      double sl = base - (StopLossCoef1 * atr1);
      double tp = base + (ProfitTargetCoef1 * atr3);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
      if(PlaceLongEntry(base, sl, tp, expiry))
         g_long_expiry = expiry;
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double base = kijun1 - (PriceEntryMult2 * atr4);
      double sl = base + (StopLossCoef2 * atr3);
      double tp = base - (ProfitTargetCoef2 * atr1);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;
      if(PlaceShortEntry(base, sl, tp, expiry))
         g_short_expiry = expiry;
   }}
}}
"""
