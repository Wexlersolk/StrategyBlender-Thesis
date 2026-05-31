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


def render_reversion_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = str(payload.get("symbol", ""))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    order_type = str(payload.get("order_type", "market")).lower()
    is_market = order_type == "market"

    long_call = f'trade.Buy(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_long");' if is_market else 'PlaceLongStop(sl, tp, expiry);'
    short_call = f'trade.Sell(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_short");' if is_market else 'PlaceShortStop(sl, tp, expiry);'

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int BBPeriod = {parse_int(params.get("BBPeriod", 20), 20)};
input double BBDev = {parse_float(params.get("BBDev", 2.0), 2.0)};
input int WPRPeriod = {parse_int(params.get("WPRPeriod", 14), 14)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 1.5), 1.5)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 2.0), 2.0)};
input double WPROversold = {parse_float(params.get("WPROversold", -80.0), -80.0)};
input double WPROverbought = {parse_float(params.get("WPROverbought", -20.0), -20.0)};

datetime g_last_bar_time = 0;
int g_bands_handle = INVALID_HANDLE;
int g_wpr_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;

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

bool PlaceLongStop(const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return false;
   double entry = NormalizeDouble(ask + MinStopDistance(), _Digits);
   return trade.BuyStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
}}

bool PlaceShortStop(const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   double entry = NormalizeDouble(bid - MinStopDistance(), _Digits);
   return trade.SellStop(InpLots, entry, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
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

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_bands_handle = iBands(_Symbol, InpTimeframe, BBPeriod, 0, BBDev, PRICE_CLOSE);
   g_wpr_handle = iWPR(_Symbol, InpTimeframe, WPRPeriod);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_bands_handle == INVALID_HANDLE || g_wpr_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   if(g_bands_handle != INVALID_HANDLE) IndicatorRelease(g_bands_handle);
   if(g_wpr_handle != INVALID_HANDLE) IndicatorRelease(g_wpr_handle);
   if(g_atr_handle != INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}}

void OnTick()
{{
   if(!IsNewBar())
      return;
   if(HasManagedPosition() || HasPendingOrders())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   if(!InBrokerTradableWindow(bar_time))
      return;

   double bb_upper_1 = 0.0, bb_lower_1 = 0.0, wpr_1 = 0.0, atr_1 = 0.0;
   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   if(!CopyValue(g_bands_handle, 1, 1, bb_upper_1)) return;
   if(!CopyValue(g_bands_handle, 2, 1, bb_lower_1)) return;
   if(!CopyValue(g_wpr_handle, 0, 1, wpr_1)) return;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;

   if({str(payload.get("debug_log", False)).lower()})
   {{
      PrintFormat("[DEBUG_TRACE] %s | bb_upper: %.5f, bb_lower: %.5f, wpr: %.2f, atr: %.5f", 
                  TimeToString(bar_time), bb_upper_1, bb_lower_1, wpr_1, atr_1);
   }}

   double open_0 = iOpen(_Symbol, InpTimeframe, 0);

   if(close_1 < bb_lower_1 && wpr_1 <= WPROversold)
   {{
      double sl = open_0 - StopLossATR * atr_1;
      double tp = open_0 + ProfitTargetATR * atr_1;
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe);
      {long_call}
      return;
   }}

   if(close_1 > bb_upper_1 && wpr_1 >= WPROverbought)
   {{
      double sl = open_0 + StopLossATR * atr_1;
      double tp = open_0 - ProfitTargetATR * atr_1;
      datetime expiry = bar_time + PeriodSeconds(InpTimeframe);
      {short_call}
   }}
}}
"""
