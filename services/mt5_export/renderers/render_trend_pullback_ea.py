from __future__ import annotations
from typing import Any
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    magic_number,
    mt5_timeframe,
    mql_broker_tradable_checks,
    normalized_export_lots,
)


def render_trend_pullback_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    direction = str(payload.get("direction", "long")).lower()
    symbol = str(payload.get("symbol", ""))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    threshold_cmp = ">" if direction == "long" else "<"
    inverse_cmp = "<=" if direction == "long" else ">="
    order_call = "Buy" if direction == "long" else "Sell"
    direction_comment = f"{strategy_id}_{direction}"
    stop_sign = "-" if direction == "long" else "+"
    target_sign = "+" if direction == "long" else "-"
    rsi_threshold = 50.0
    order_type = str(payload.get("order_type", "market")).lower()
    is_market = order_type == "market"

    if is_market:
        entry_call = f'trade.{order_call}(InpLots, _Symbol, 0.0, sl, tp, "{direction_comment}");'
    else:
        entry_call = "PlaceEntry(sl, tp, expiry);"

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int FastEMA = {parse_int(params.get("FastEMA", 20), 20)};
input int SlowEMA = {parse_int(params.get("SlowEMA", 50), 50)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int ExitAfterBars = {parse_int(params.get("ExitAfterBars", 12), 12)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 3.0), 3.0)};
input int WaveTrendChannel = {parse_int(params.get("WaveTrendChannel", 9), 9)};
input int WaveTrendAverage = {parse_int(params.get("WaveTrendAverage", 21), 21)};

datetime g_last_bar_time = 0;
int g_ema_fast_handle = INVALID_HANDLE;
int g_ema_slow_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
int g_position_bars = 0;

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

double MinStopDistance()
{{
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;
   return MathMax((double)stops_level * point, point);
}}

void WaveTrend(const int shift, double &wt_main, double &wt_signal)
{{
   int channel_len = WaveTrendChannel;
   int avg_len = WaveTrendAverage;
   int sig_len = 4;
   int lb = MathMax(250, (channel_len + avg_len) * 5 + sig_len);

   double esa[]; ArraySetAsSeries(esa, true); ArrayResize(esa, lb);
   double d[]; ArraySetAsSeries(d, true); ArrayResize(d, lb);
   
   for(int i = lb - 1; i >= 0; --i)
   {{
      double cap = (iHigh(_Symbol, InpTimeframe, shift + i) + iLow(_Symbol, InpTimeframe, shift + i) + iClose(_Symbol, InpTimeframe, shift + i)) / 3.0;
      double pesa = (i == lb - 1) ? cap : esa[i + 1];
      esa[i] = pesa + (2.0 / (channel_len + 1.0)) * (cap - pesa);
      double pd = (i == lb - 1) ? 0.0 : d[i + 1];
      d[i] = pd + (2.0 / (channel_len + 1.0)) * (MathAbs(cap - esa[i]) - pd);
   }}
   
   double ci[]; ArraySetAsSeries(ci, true); ArrayResize(ci, lb);
   for(int i = 0; i < lb; ++i) ci[i] = (iHigh(_Symbol, InpTimeframe, shift+i) + iLow(_Symbol, InpTimeframe, shift+i) + iClose(_Symbol, InpTimeframe, shift+i)) / 3.0 - esa[i];
   for(int i = 0; i < lb; ++i) ci[i] /= (0.015 * d[i] + 1e-9);
   
   double tci[]; ArraySetAsSeries(tci, true); ArrayResize(tci, lb);
   for(int i = lb - 1; i >= 0; --i)
   {{
      double ptci = (i == lb - 1) ? ci[i] : tci[i + 1];
      tci[i] = ptci + (2.0 / (avg_len + 1.0)) * (ci[i] - ptci);
   }}
   
   wt_main = tci[0];
   double sma_sig = 0.0;
   for(int i = 0; i < sig_len; ++i) sma_sig += tci[i];
   wt_signal = sma_sig / sig_len;
}}

bool PlaceEntry(const double sl, const double tp, const datetime expiry)
{{
   double distance = MinStopDistance();
   if("{direction}" == "long")
   {{
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(ask <= 0.0)
         return false;
      double entry = NormalizeDouble(ask + distance, _Digits);
      return trade.BuyStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{direction_comment}");
   }}
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   double entry = NormalizeDouble(bid - distance, _Digits);
   return trade.SellStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{direction_comment}");
}}

bool HasManagedPosition()
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

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_fast_handle = iMA(_Symbol, InpTimeframe, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_slow_handle = iMA(_Symbol, InpTimeframe, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_ema_fast_handle == INVALID_HANDLE || g_ema_slow_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_ema_fast_handle != INVALID_HANDLE) IndicatorRelease(g_ema_fast_handle);
   if(g_ema_slow_handle != INVALID_HANDLE) IndicatorRelease(g_ema_slow_handle);
   if(g_atr_handle != INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InBrokerTradableWindow(bar_time))
      return;

   if(HasManagedPosition() || HasPendingOrders())
   {{
      if(HasManagedPosition())
      {{
         g_position_bars++;
         if(g_position_bars >= ExitAfterBars)
         {{
            CloseManagedPositions();
            g_position_bars = 0;
         }}
      }}
      return;
   }}
   g_position_bars = 0;

   double ema_fast_1 = 0.0, ema_slow_1 = 0.0, atr_1 = 0.0;
   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1)) return;
   if(!CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1)) return;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;

   double wt_main_1 = 0.0, wt_sig_1 = 0.0;
   WaveTrend(1, wt_main_1, wt_sig_1);

   bool trend_ok = (ema_fast_1 {threshold_cmp} ema_slow_1);
   bool pullback_ok = (close_1 {inverse_cmp} ema_fast_1);
   bool wave_ok = (wt_main_1 {threshold_cmp} wt_sig_1);
   
   if({str(payload.get("debug_log", False)).lower()})
   {{
      PrintFormat("[DEBUG_TRACE] %s | ema_fast: %.5f, ema_slow: %.5f, atr: %.5f, wt_main: %.5f, wt_sig: %.5f, trend: %d, pull: %d, wave: %d", 
                  TimeToString(bar_time), ema_fast_1, ema_slow_1, atr_1, wt_main_1, wt_sig_1, trend_ok, pullback_ok, wave_ok);
   }}

   if(!(trend_ok && pullback_ok && wave_ok))
      return;

   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   double sl = open_0 {stop_sign} StopLossATR * atr_1;
   double tp = open_0 {target_sign} ProfitTargetATR * atr_1;
   datetime expiry = bar_time + PeriodSeconds(InpTimeframe);
   {entry_call}
}}
"""
