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

def render_sqx_usdjpy_ichi_keltner_ea(strategy_id: str, payload: dict[str, Any]) -> str:
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
input int IchimokuTenkan = {parse_int(params.get("IchimokuTenkan", 9), 9)};
input int IchimokuKijun = {parse_int(params.get("IchimokuKijun", 26), 26)};
input int IchimokuSenkou = {parse_int(params.get("IchimokuSenkou", 52), 52)};
input int KeltnerPeriod = {parse_int(params.get("KeltnerPeriod", 20), 20)};
input double KeltnerMult = {parse_float(params.get("KeltnerMult", 2.0), 2.0)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 4.0), 4.0)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};

int g_ichi_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;
datetime g_last_trade_bar = 0; // Tracks the bar time of the last opened position to prevent multiple trades per bar

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ichi_handle = iIchimoku(_Symbol, InpTimeframe, IchimokuTenkan, IchimokuKijun, IchimokuSenkou);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   if(g_ichi_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE) return INIT_FAILED;
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

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double senkou_a_1 = 0.0, senkou_b_1 = 0.0;
   if(!CopyValue(g_ichi_handle, 2, 1, senkou_a_1) || !CopyValue(g_ichi_handle, 3, 1, senkou_b_1)) return;
   
   double sum = 0.0;
   for(int i=1; i<=KeltnerPeriod; i++) sum += iClose(_Symbol, InpTimeframe, i);
   double mid = sum / KeltnerPeriod;
   
   double atr_1 = 0.0;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;
   
   double kc_upper = mid + KeltnerMult * atr_1;
   double kc_lower = mid - KeltnerMult * atr_1;

   if(close_1 > senkou_a_1 && close_1 > senkou_b_1 && close_1 < kc_lower)
   {{
      double sl = close_1 - StopLossATR * atr_1;
      double tp = close_1 + ProfitTargetATR * atr_1;
      trade.Buy(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_long");
   }}
   else if(close_1 < senkou_a_1 && close_1 < senkou_b_1 && close_1 > kc_upper)
   {{
      double sl = close_1 + StopLossATR * atr_1;
      double tp = close_1 - ProfitTargetATR * atr_1;
      trade.Sell(InpLots, _Symbol, 0, sl, tp, "{strategy_id}_short");
   }}
}}
"""
