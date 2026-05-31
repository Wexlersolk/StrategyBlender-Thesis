from __future__ import annotations
from typing import Any
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    normalized_export_lots,
    magic_number,
    mt5_timeframe,
    mql_broker_tradable_checks,
)

def render_us100_ny_momentum_v3_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H1"))
    symbol = str(payload.get("symbol", ""))
    
    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mql_tf};
input double InpLots = {normalized_export_lots(payload.get("symbol", ""), params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int EMAPeriod = {parse_int(params.get("EMAPeriod", 100), 100)};
input int PullbackEMAPeriod = {parse_int(params.get("PullbackEMAPeriod", 20), 20)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int ADXPeriod = {parse_int(params.get("ADXPeriod", 14), 14)};
input double ADXMin = {parse_float(params.get("ADXMin", 20.0), 20.0)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.5), 2.5)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 6.0), 6.0)};
input double TrailingStopATR = {parse_float(params.get("TrailingStopATR", 1.5), 1.5)};
input int NYOpenHour = {parse_int(params.get("NYOpenHour", 14), 14)};
input int NYCloseHour = {parse_int(params.get("NYCloseHour", 18), 18)};

int g_ema_trend_handle = INVALID_HANDLE;
int g_ema_pullback_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
int g_adx_handle = INVALID_HANDLE;
datetime g_last_bar_time = 0;

int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_trend_handle = iMA(_Symbol, InpTimeframe, EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_pullback_handle = iMA(_Symbol, InpTimeframe, PullbackEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   g_adx_handle = iADX(_Symbol, InpTimeframe, ADXPeriod);
   
   if(g_ema_trend_handle == INVALID_HANDLE || g_ema_pullback_handle == INVALID_HANDLE || 
      g_atr_handle == INVALID_HANDLE || g_adx_handle == INVALID_HANDLE)
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

void OnDeinit(const int reason)
{{
   IndicatorRelease(g_ema_trend_handle);
   IndicatorRelease(g_ema_pullback_handle);
   IndicatorRelease(g_atr_handle);
   IndicatorRelease(g_adx_handle);
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

void CloseAllPositions()
{{
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      trade.PositionClose(ticket);
   }}
}}

void ApplyTrailingStop(const double atr_val)
{{
   if(TrailingStopATR <= 0) return;
   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      
      double current_sl = PositionGetDouble(POSITION_SL);
      double current_tp = PositionGetDouble(POSITION_TP);
      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      
      if(type == POSITION_TYPE_BUY)
      {{
         double new_sl = bid - atr_val * TrailingStopATR;
         if(new_sl > current_sl + _Point)
            trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), current_tp);
      }}
      else if(type == POSITION_TYPE_SELL)
      {{
         double new_sl = ask + atr_val * TrailingStopATR;
         if(current_sl == 0 || new_sl < current_sl - _Point)
            trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), current_tp);
      }}
   }}
}}

void OnTick()
{{
   datetime now = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(now, dt);

   // Trailing stop logic (every tick)
   double atr_val = 0;
   if(CopyValue(g_atr_handle, 0, 1, atr_val))
      ApplyTrailingStop(atr_val);

   // Exit logic
   if(dt.hour >= NYCloseHour)
   {{
      CloseAllPositions();
      return;
   }}

   if(!IsNewBar()) return;
   if(dt.hour != NYOpenHour) return;
   if(HasOpenPosition()) return;

   double trend_ema = 0, pullback_ema = 0, adx_val = 0;
   if(!CopyValue(g_ema_trend_handle, 0, 1, trend_ema) ||
      !CopyValue(g_ema_pullback_handle, 0, 1, pullback_ema) ||
      !CopyValue(g_adx_handle, 0, 1, adx_val)) return;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double low_1 = iLow(_Symbol, InpTimeframe, 1);
   double high_1 = iHigh(_Symbol, InpTimeframe, 1);

   // Long Entry
   if(close_1 > trend_ema && low_1 < pullback_ema && adx_val > ADXMin)
   {{
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = bid - atr_val * StopLossATR;
      double tp = bid + atr_val * ProfitTargetATR;
      trade.Buy(InpLots, _Symbol, bid, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), "{strategy_id}_long");
   }}
   // Short Entry
   else if(close_1 < trend_ema && high_1 > pullback_ema && adx_val > ADXMin)
   {{
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = ask + atr_val * StopLossATR;
      double tp = ask - atr_val * ProfitTargetATR;
      trade.Sell(InpLots, _Symbol, ask, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), "{strategy_id}_short");
   }}
}}
"""
