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

def render_sqx_us100_nasdaq_qqe_ea(strategy_id: str, payload: dict[str, Any]) -> str:
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
input int QQERsiPeriod1 = {parse_int(params.get("QQERsiPeriod1", 14), 14)};
input int QQESmooth1 = {parse_int(params.get("QQESmooth1", 5), 5)};
input int QQERsiPeriod2 = {parse_int(params.get("QQERsiPeriod2", 69), 69)};
input int QQESmooth2 = {parse_int(params.get("QQESmooth2", 5), 5)};
input int SMAEntryPeriod1 = {parse_int(params.get("SMAEntryPeriod1", 53), 53)};
input int SessionLowLookback = {parse_int(params.get("SessionLowLookback", 14), 14)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 40), 40)};
input int ATRPeriod2 = {parse_int(params.get("ATRPeriod2", 19), 19)};
input int ATRPeriod3 = {parse_int(params.get("ATRPeriod3", 14), 14)};
input int ATRPeriod4 = {parse_int(params.get("ATRPeriod4", 10), 10)};
input double PriceEntryMult1 = {parse_float(params.get("PriceEntryMult1", 1.2), 1.2)};
input double PriceEntryMult2 = {parse_float(params.get("PriceEntryMult2", 0.9), 0.9)};
input int ExitAfterBars1 = {parse_int(params.get("ExitAfterBars1", 18), 18)};
input int ExitAfterBars2 = {parse_int(params.get("ExitAfterBars2", 19), 19)};
input double ProfitTargetCoef1 = {parse_float(params.get("ProfitTargetCoef1", 4.2), 4.2)};
input double StopLossCoef1 = {parse_float(params.get("StopLossCoef1", 1.9), 1.9)};
input double ProfitTargetCoef2 = {parse_float(params.get("ProfitTargetCoef2", 3.7), 3.7)};
input double StopLossCoef2 = {parse_float(params.get("StopLossCoef2", 1.7), 1.7)};
input double TrailingStopCoef1 = {parse_float(params.get("TrailingStopCoef1", 1.0), 1.0)};
input double TrailingStop1 = {parse_float(params.get("TrailingStop1", 105.0), 105.0)};
input double TrailingActivation1 = {parse_float(params.get("TrailingActivation1", 45.0), 45.0)};
input int LongExpiryBars = 1;
input int ShortExpiryBars = 1;

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
int g_rsi1_handle = INVALID_HANDLE;
int g_rsi2_handle = INVALID_HANDLE;
int g_qqe_main1_handle = INVALID_HANDLE;
int g_qqe_sig1_handle = INVALID_HANDLE;
int g_qqe_main2_handle = INVALID_HANDLE;
int g_qqe_sig2_handle = INVALID_HANDLE;
int g_sma_entry_handle = INVALID_HANDLE;
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

int HeldBars(const datetime bar_time, const datetime entry_time)
{{
   if(entry_time == 0)
      return 0;
   return (int)((bar_time - entry_time) / PeriodSeconds(InpTimeframe));
}}

void ManageTimedExits(const datetime bar_time)
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

      ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      datetime entry_time = (datetime)PositionGetInteger(POSITION_TIME);
      int bars = HeldBars(bar_time, entry_time);
      if(pos_type == POSITION_TYPE_BUY && ExitAfterBars1 > 0 && bars >= ExitAfterBars1)
         trade.PositionClose(ticket);
      if(pos_type == POSITION_TYPE_SELL && ExitAfterBars2 > 0 && bars >= ExitAfterBars2)
         trade.PositionClose(ticket);
   }}
}}

void ComputeHeikenAshiShift(const int target_shift, double &ha_open, double &ha_close)
{{
   int total_bars = Bars(_Symbol, InpTimeframe);
   if(total_bars <= target_shift + 1)
   {{
      ha_open = 0.0;
      ha_close = 0.0;
      return;
   }}

   int start_shift = MathMin(total_bars - 2, target_shift + 60);
   double seed_open = iOpen(_Symbol, InpTimeframe, start_shift);
   double seed_close = iClose(_Symbol, InpTimeframe, start_shift);
   if(seed_open == 0.0 || seed_close == 0.0)
   {{
      ha_open = 0.0;
      ha_close = 0.0;
      return;
   }}

   double prev_ha_open = seed_open;
   double prev_ha_close = seed_close;
   for(int shift = start_shift; shift >= target_shift; --shift)
   {{
      double open_ = iOpen(_Symbol, InpTimeframe, shift);
      double high_ = iHigh(_Symbol, InpTimeframe, shift);
      double low_ = iLow(_Symbol, InpTimeframe, shift);
      double close_ = iClose(_Symbol, InpTimeframe, shift);
      ha_close = (open_ + high_ + low_ + close_) / 4.0;
      ha_open = (prev_ha_open + prev_ha_close) / 2.0;
      prev_ha_open = ha_open;
      prev_ha_close = ha_close;
   }}
}}

double HAFloor(const int shift)
{{
   double ha_open = 0.0, ha_close = 0.0;
   ComputeHeikenAshiShift(shift, ha_open, ha_close);
   double low_ = iLow(_Symbol, InpTimeframe, shift);
   if(low_ == 0.0 || ha_open == 0.0 || ha_close == 0.0)
      return 0.0;
   return MathMin(low_, MathMin(ha_open, ha_close));
}}

double SessionFloor(const int shift)
{{
   double value = DBL_MAX;
   for(int idx = shift; idx < shift + SessionLowLookback; ++idx)
   {{
      double low_ = iLow(_Symbol, InpTimeframe, idx);
      if(low_ == 0.0)
         continue;
      value = MathMin(value, low_);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

bool LongSignal()
{{
   double main_1 = 0.0, sig_1 = 0.0;
   if(!CopyValue(g_qqe_main1_handle, 0, 1, main_1) || !CopyValue(g_qqe_sig1_handle, 0, 1, sig_1))
      return false;
   return main_1 > sig_1;
}}

bool ShortSignal()
{{
   double main_1 = 0.0, sig_1 = 0.0;
   if(!CopyValue(g_qqe_main1_handle, 0, 1, main_1) || !CopyValue(g_qqe_sig1_handle, 0, 1, sig_1))
      return false;
   return main_1 < sig_1;
}}

bool LongExitSignal()
{{
   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double floor_1 = SessionFloor(1);
   if(close_1 == 0.0 || floor_1 == 0.0)
      return false;
   return close_1 <= floor_1;
}}

bool ShortExitSignal()
{{
   double main_2 = 0.0, sig_2 = 0.0;
   if(!CopyValue(g_qqe_main2_handle, 0, 1, main_2) || !CopyValue(g_qqe_sig2_handle, 0, 1, sig_2))
      return false;
   return main_2 > sig_2;
}}

void ManageTrailingStops()
{{
   double atr4 = 0.0;
   if(!CopyValue(g_atr4_handle, 0, 1, atr4))
      return;

   double long_trail = TrailingStopCoef1 * atr4;
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
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);

      if(pos_type == POSITION_TYPE_BUY && long_trail > 0.0)
      {{
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double new_sl = bid - long_trail;
         if(sl == 0.0 || new_sl > sl)
            trade.PositionModify(ticket, new_sl, tp);
      }}

      if(pos_type == POSITION_TYPE_SELL && TrailingStop1 > 0.0 && TrailingActivation1 > 0.0)
      {{
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit_distance = open_price - ask;
         if(profit_distance < TrailingActivation1)
            continue;
         double new_sl = ask + TrailingStop1;
         if(sl == 0.0 || new_sl < sl)
            trade.PositionModify(ticket, new_sl, tp);
      }}
   }}
}}

bool PlaceLongEntry(const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(entry_price <= ask)
      return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
   return trade.BuyStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
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
   g_rsi1_handle = iRSI(_Symbol, InpTimeframe, QQERsiPeriod1, PRICE_CLOSE);
   g_rsi2_handle = iRSI(_Symbol, InpTimeframe, QQERsiPeriod2, PRICE_CLOSE);
   g_qqe_main1_handle = iMA(_Symbol, InpTimeframe, QQESmooth1, 0, MODE_SMA, g_rsi1_handle);
   g_qqe_sig1_handle = iMA(_Symbol, InpTimeframe, QQESmooth1 + 1, 0, MODE_SMA, g_qqe_main1_handle);
   g_qqe_main2_handle = iMA(_Symbol, InpTimeframe, QQESmooth2, 0, MODE_SMA, g_rsi2_handle);
   g_qqe_sig2_handle = iMA(_Symbol, InpTimeframe, QQESmooth2 + 1, 0, MODE_SMA, g_qqe_main2_handle);
   g_sma_entry_handle = iMA(_Symbol, InpTimeframe, SMAEntryPeriod1, 0, MODE_SMA, PRICE_MEDIAN);
   g_atr1_handle = iATR(_Symbol, InpTimeframe, ATRPeriod1);
   g_atr2_handle = iATR(_Symbol, InpTimeframe, ATRPeriod2);
   g_atr3_handle = iATR(_Symbol, InpTimeframe, ATRPeriod3);
   g_atr4_handle = iATR(_Symbol, InpTimeframe, ATRPeriod4);
   if(g_rsi1_handle == INVALID_HANDLE || g_rsi2_handle == INVALID_HANDLE || g_qqe_main1_handle == INVALID_HANDLE || g_qqe_sig1_handle == INVALID_HANDLE || g_qqe_main2_handle == INVALID_HANDLE || g_qqe_sig2_handle == INVALID_HANDLE || g_sma_entry_handle == INVALID_HANDLE || g_atr1_handle == INVALID_HANDLE || g_atr2_handle == INVALID_HANDLE || g_atr3_handle == INVALID_HANDLE || g_atr4_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_rsi1_handle != INVALID_HANDLE) IndicatorRelease(g_rsi1_handle);
   if(g_rsi2_handle != INVALID_HANDLE) IndicatorRelease(g_rsi2_handle);
   if(g_qqe_main1_handle != INVALID_HANDLE) IndicatorRelease(g_qqe_main1_handle);
   if(g_qqe_sig1_handle != INVALID_HANDLE) IndicatorRelease(g_qqe_sig1_handle);
   if(g_qqe_main2_handle != INVALID_HANDLE) IndicatorRelease(g_qqe_main2_handle);
   if(g_qqe_sig2_handle != INVALID_HANDLE) IndicatorRelease(g_qqe_sig2_handle);
   if(g_sma_entry_handle != INVALID_HANDLE) IndicatorRelease(g_sma_entry_handle);
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

   if(LongExitSignal() || ShortExitSignal())
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

         ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         if(pos_type == POSITION_TYPE_BUY && LongExitSignal())
            trade.PositionClose(ticket);
         if(pos_type == POSITION_TYPE_SELL && ShortExitSignal())
            trade.PositionClose(ticket);
      }}
   }}

   ManageTimedExits(bar_time);
   CancelExpiredOrders(bar_time);
   if(HasOpenPosition() || HasPendingOrders() || !InTimeWindow(bar_time))
      return;

   bool long_signal = LongSignal();
   bool short_signal = ShortSignal();
   double atr1 = 0.0, atr2 = 0.0, atr3 = 0.0, atr4 = 0.0, sma_entry = 0.0;
   if(!CopyValue(g_atr1_handle, 0, 1, atr1) || !CopyValue(g_atr2_handle, 0, 1, atr2) || !CopyValue(g_atr3_handle, 0, 1, atr3) || !CopyValue(g_atr4_handle, 0, 1, atr4) || !CopyValue(g_sma_entry_handle, 0, 1, sma_entry))
      return;

   if(long_signal)
   {{
      double base = HAFloor(1) + (PriceEntryMult1 * atr1);
      if(base <= 0.0)
         return;
      double sl = base - (StopLossCoef1 * atr3);
      double tp = base + (ProfitTargetCoef1 * atr2);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * LongExpiryBars;
      if(PlaceLongEntry(base, sl, tp, expiry))
         g_long_expiry = expiry;
      return;
   }}

   if(short_signal && !long_signal)
   {{
      double base = sma_entry - (PriceEntryMult2 * atr3);
      if(base <= 0.0)
         return;
      double sl = base + (StopLossCoef2 * atr3);
      double tp = base - (ProfitTargetCoef2 * atr3);
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * ShortExpiryBars;
      if(PlaceShortEntry(base, sl, tp, expiry))
         g_short_expiry = expiry;
   }}
}}
"""
