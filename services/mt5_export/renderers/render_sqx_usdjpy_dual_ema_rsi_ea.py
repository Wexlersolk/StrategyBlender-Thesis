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

def render_sqx_usdjpy_dual_ema_rsi_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int FastEMA = {parse_int(params.get("FastEMA", 21), 21)};
input int SlowEMA = {parse_int(params.get("SlowEMA", 55), 55)};
input int RSIPeriod = {parse_int(params.get("RSIPeriod", 14), 14)};
input double RSIThreshold = {parse_float(params.get("RSIThreshold", 55.0), 55.0)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 1.8), 1.8)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 3.6), 3.6)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};

int g_ema_f_handle = INVALID_HANDLE;
int g_ema_s_handle = INVALID_HANDLE;
int g_rsi_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;
datetime g_last_trade_bar = 0; // Tracks the bar time of the last opened position to prevent multiple trades per bar

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_f_handle = iMA(_Symbol, InpTimeframe, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_s_handle = iMA(_Symbol, InpTimeframe, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_rsi_handle = iRSI(_Symbol, InpTimeframe, RSIPeriod, PRICE_CLOSE);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_ema_f_handle == INVALID_HANDLE || g_ema_s_handle == INVALID_HANDLE || g_rsi_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
      return INIT_FAILED;
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
      if(type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_BUY_LIMIT || type == ORDER_TYPE_SELL_LIMIT)
         return true;
   }}
   return false;
}}

void OnTick()
{{
   if(HasOpenPosition())
   {{
      // Record that we have a position open for the current bar to prevent re-entry if it closes early
      g_last_trade_bar = iTime(_Symbol, InpTimeframe, 0);
   }}

   if(!IsNewBar()) return;
   
   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   
   // HARD TRADE LIMIT: Max 1 trade per bar.
   // This prevents "loss loops" where a position is opened and stopped out multiple times within a single H4 bar.
   if(HasOpenPosition() || HasPendingOrders() || bar_time <= g_last_trade_bar) return;

   double ema_f_1 = 0.0, ema_f_2 = 0.0;
   double ema_s_1 = 0.0, ema_s_2 = 0.0;
   if(!CopyValue(g_ema_f_handle, 0, 1, ema_f_1) || !CopyValue(g_ema_f_handle, 0, 2, ema_f_2)) return;
   if(!CopyValue(g_ema_s_handle, 0, 1, ema_s_1) || !CopyValue(g_ema_s_handle, 0, 2, ema_s_2)) return;
   
   double rsi_1 = 0.0;
   if(!CopyValue(g_rsi_handle, 0, 1, rsi_1)) return;
   double atr_1 = 0.0;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;
   double close_1 = iClose(_Symbol, InpTimeframe, 1);

   bool long_cross = (ema_f_2 <= ema_s_2 && ema_f_1 > ema_s_1);
   bool short_cross = (ema_f_2 >= ema_s_2 && ema_f_1 < ema_s_1);

   if(long_cross && rsi_1 > RSIThreshold)
   {{
      double sl = close_1 - StopLossATR * atr_1;
      double tp = close_1 + ProfitTargetATR * atr_1;
      trade.Buy(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_long");
   }}
   else if(short_cross && rsi_1 < (100.0 - RSIThreshold))
   {{
      double sl = close_1 + StopLossATR * atr_1;
      double tp = close_1 - ProfitTargetATR * atr_1;
      trade.Sell(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_short");
   }}
}}
"""
