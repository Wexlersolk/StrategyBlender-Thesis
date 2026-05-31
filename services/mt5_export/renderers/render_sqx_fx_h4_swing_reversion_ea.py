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

def render_sqx_fx_h4_swing_reversion_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H4"))
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int BBPeriod = {parse_int(params.get("BBPeriod", 20), 20)};
input double BBMult = {parse_float(params.get("BBMult", 2.0), 2.0)};
input int WPRPeriod = {parse_int(params.get("WPRPeriod", 14), 14)};
input double WPROversold = {parse_float(params.get("WPROversold", -80.0), -80.0)};
input double WPROverbought = {parse_float(params.get("WPROverbought", -20.0), -20.0)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 3.0), 3.0)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};

int g_bb_handle = INVALID_HANDLE;
int g_wpr_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_bb_handle = iBands(_Symbol, InpTimeframe, BBPeriod, 0, BBMult, PRICE_CLOSE);
   g_wpr_handle = iWPR(_Symbol, InpTimeframe, WPRPeriod);
   // Match Python sq_atr (Wilder's smoothing)
   g_atr_handle = iMA(_Symbol, InpTimeframe, ATRPeriod, 0, MODE_SMMA, iATR(_Symbol, InpTimeframe, 1));
   if(g_bb_handle == INVALID_HANDLE || g_wpr_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
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
   if(!IsNewBar()) return;
   if(PositionsTotal() > 0 || HasPendingOrders()) return;

   double bb_up_1 = 0.0, bb_low_1 = 0.0, wpr_1 = 0.0, atr_1 = 0.0;
   if(!CopyValue(g_bb_handle, 1, 1, bb_up_1) || !CopyValue(g_bb_handle, 2, 1, bb_low_1)) return;
   if(!CopyValue(g_wpr_handle, 0, 1, wpr_1) || !CopyValue(g_atr_handle, 0, 1, atr_1)) return;
   
   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double low_1 = iLow(_Symbol, InpTimeframe, 1);
   double high_1 = iHigh(_Symbol, InpTimeframe, 1);

   if(low_1 < bb_low_1 && wpr_1 < WPROversold)
   {{
      double sl = close_1 - StopLossATR * atr_1;
      double tp = close_1 + ProfitTargetATR * atr_1;
      trade.Buy(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_long");
   }}
   else if(high_1 > bb_up_1 && wpr_1 > WPROverbought)
   {{
      double sl = close_1 + StopLossATR * atr_1;
      double tp = close_1 - ProfitTargetATR * atr_1;
      trade.Sell(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_short");
   }}
}}
"""
