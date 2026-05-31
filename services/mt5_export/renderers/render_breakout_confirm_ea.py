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

def render_breakout_confirm_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H4"))
    direction = str(payload.get("direction", "long")).lower()
    symbol = str(payload.get("symbol", ""))
    
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 20), 20)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 20), 20)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int BBWRPeriod = {parse_int(params.get("BBWRPeriod", 20), 20)};
input int EMAPeriod = {parse_int(params.get("EMAPeriod", 200), 200)};
input double BBWRMin = {parse_float(params.get("BBWRMin", 0.0), 0.0)};
input double MaxDistancePct = {parse_float(params.get("MaxDistancePct", 3.0), 3.0)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 3.0), 3.0)};

int g_atr_handle = INVALID_HANDLE;
int g_bands_handle = INVALID_HANDLE;
int g_ema_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;
int g_log_handle = INVALID_HANDLE;

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

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_bands_handle = iBands(_Symbol, InpTimeframe, BBWRPeriod, 0, 2.0, PRICE_CLOSE);
   g_ema_handle = iMA(_Symbol, InpTimeframe, EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   
   if(g_bands_handle == INVALID_HANDLE || g_ema_handle == INVALID_HANDLE)
      return INIT_FAILED;
      
   string filename = "debug_us30_indicators.csv";
   g_log_handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(g_log_handle != INVALID_HANDLE)
      FileWrite(g_log_handle, "Time", "Close", "ATR", "BBWR", "EMA", "Level");

   return INIT_SUCCEEDED;
}}

bool CopyValue(const int handle, const int buffer, const int shift, double &value)
{{
   double tmp[];
   ArraySetAsSeries(tmp, true);
   if(CopyBuffer(handle, buffer, shift, 1, tmp) < 1) return false;
   value = tmp[0];
   return true;
}}

bool IsNewBar()
{{
   datetime current_bar = iTime(_Symbol, InpTimeframe, 0);
   if(current_bar == 0) return false;
   if(current_bar != g_last_bar_time)
   {{
      g_last_bar_time = current_bar;
      return true;
   }}
   return false;
}}

void OnDeinit(const int reason)
{{
   if(g_bands_handle != INVALID_HANDLE)
      IndicatorRelease(g_bands_handle);
   if(g_ema_handle != INVALID_HANDLE)
      IndicatorRelease(g_ema_handle);
   if(g_log_handle != INVALID_HANDLE)
      FileClose(g_log_handle);
}}

bool InBrokerTradableWindow(const datetime when)
{{
   return true;
}}

double MinStopDistance()
{{
   long stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(point <= 0.0)
      point = _Point;
   return MathMax((double)stops_level * point, point);
}}

bool PlaceLongStop(const double reference_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return false;
   double entry = MathMax(reference_price, ask + MinStopDistance());
   return trade.BuyStop(InpLots, NormalizeDouble(entry, _Digits), _Symbol, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
}}

bool PlaceShortStop(const double reference_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   double entry = MathMin(reference_price, bid - MinStopDistance());
   return trade.SellStop(InpLots, NormalizeDouble(entry, _Digits), _Symbol, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
}}

bool HasOpenPosition()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
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

void OnTick()
{{
   if(!IsNewBar()) return;
   
   // Get ATR manually to match Wilder's formula
   double atr_1 = 0;
   double prev_atr_calc = 0;
   for(int i=ATRPeriod*10; i>=1; i--) {{
      double h = iHigh(_Symbol, InpTimeframe, i);
      double l = iLow(_Symbol, InpTimeframe, i);
      double pc = iClose(_Symbol, InpTimeframe, i+1);
      if(h==0 || l==0 || pc==0) continue;
      double tr = MathMax(h-l, MathMax(MathAbs(h-pc), MathAbs(l-pc)));
      if(prev_atr_calc == 0) prev_atr_calc = h-l;
      else prev_atr_calc = (prev_atr_calc * (ATRPeriod - 1) + tr) / ATRPeriod;
   }}
   atr_1 = prev_atr_calc;

   double bb_mid = 0.0, bb_upper = 0.0, bb_lower = 0.0, ema_1 = 0.0;
   if(!CopyValue(g_bands_handle, 0, 1, bb_mid) ||
      !CopyValue(g_bands_handle, 1, 1, bb_upper) ||
      !CopyValue(g_bands_handle, 2, 1, bb_lower) ||
      !CopyValue(g_ema_handle, 0, 1, ema_1)) 
   {{
      return;
   }}
   
   double bbwr_1 = 0.0;
   if(MathAbs(bb_mid) > 1e-8)
      bbwr_1 = (bb_upper - bb_lower) / bb_mid * 100.0;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   double level_s = ("{direction}" == "long") ? HighestHigh(HighestPeriod, 2) : LowestLow(LowestPeriod, 2);

   if(g_log_handle != INVALID_HANDLE)
      FileWrite(g_log_handle, TimeToString(iTime(_Symbol, InpTimeframe, 0)), close_1, atr_1, bbwr_1, ema_1, level_s);

   if(HasOpenPosition() || HasPendingOrders()) return;

   if("{direction}" == "long")
   {{
      double level_signal = HighestHigh(HighestPeriod, 2);
      double level_entry = level_signal;
      
      if(level_signal <= 0.0) return;
      if(close_1 > level_signal && bbwr_1 >= BBWRMin && open_0 > ema_1)
      {{
         double dist = MathAbs(level_entry - open_0) / MathMax(open_0, 1e-9) * 100.0;
         if(dist <= MaxDistancePct)
         {{
            double sl = level_entry - StopLossATR * atr_1;
            double tp = level_entry + ProfitTargetATR * atr_1;
            datetime expiry = iTime(_Symbol, InpTimeframe, 0) + PeriodSeconds(InpTimeframe) * 3;
            PlaceLongStop(level_entry, sl, tp, expiry);
         }}
      }}
   }}
   else
   {{
      double level_signal = LowestLow(LowestPeriod, 2);
      double level_entry = level_signal;
      
      if(level_signal <= 0.0) return;
      if(close_1 < level_signal && bbwr_1 >= BBWRMin && open_0 < ema_1)
      {{
         double dist = MathAbs(level_entry - open_0) / MathMax(open_0, 1e-9) * 100.0;
         if(dist <= MaxDistancePct)
         {{
            double sl = level_entry + StopLossATR * atr_1;
            double tp = level_entry - ProfitTargetATR * atr_1;
            datetime expiry = iTime(_Symbol, InpTimeframe, 0) + PeriodSeconds(InpTimeframe) * 3;
            PlaceShortStop(level_entry, sl, tp, expiry);
         }}
      }}
   }}
}}
"""
