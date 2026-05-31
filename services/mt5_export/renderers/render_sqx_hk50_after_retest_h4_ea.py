from __future__ import annotations
from typing import Any
from config import settings
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    signal_window_params,
    normalized_export_lots,
    magic_number,
    mt5_timeframe,
    mql_broker_tradable_checks,
)

def render_sqx_hk50_after_retest_h4_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = payload.get("symbol", "HK50.cash")
    tf_str = payload.get("timeframe", "H4")
    trend_bias_mode = str(payload.get("trend_bias_mode", "sar_bias")).strip().lower()
    entry_style = str(payload.get("entry_style", "stop")).strip().lower()

    defaults = settings.symbol_execution_defaults(symbol)
    friday_flat_hhmm = str(defaults.get("force_flat_hhmm", "11:30"))
    friday_flat_hour = parse_int(friday_flat_hhmm[:2], 11)
    friday_flat_minute = parse_int(friday_flat_hhmm[3:], 30)
    
    signal_from, signal_to = signal_window_params(
        symbol,
        params,
        default_from="00:13",
        default_to="00:26",
    )

    # Signal logic mapping
    if trend_bias_mode == "ichimoku_bias":
        long_condition = "close > ichi_kijun && adx_plus > adx_minus"
        short_condition = "close < ichi_kijun && adx_minus > adx_plus"
    elif trend_bias_mode == "adx_bias":
        long_condition = "adx_plus_2 > adx_plus_3 && adx_plus_3 > adx_plus_4 && adx_plus > adx_minus"
        short_condition = "adx_minus_2 > adx_minus_3 && adx_minus_3 > adx_minus_4 && adx_minus > adx_plus"
    else: # sar_bias
        long_condition = "adx_plus_3 > adx_plus_4 && adx_plus_4 > adx_plus_5 && adx_plus > adx_minus && close > sar"
        short_condition = "adx_minus_3 > adx_minus_4 && adx_minus_4 > adx_minus_5 && adx_minus > adx_plus && close < sar"

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mt5_timeframe(tf_str)};
input double InpLots = {normalized_export_lots(symbol, params, default=1.0, payload=payload)};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Parameters"
input int DIPeriod1 = {parse_int(params.get("DIPeriod1", 14), 14)};
input double SARStep = {parse_float(params.get("SARStep", 0.266), 0.266)};
input double SARMax = {parse_float(params.get("SARMax", 0.69), 0.69)};
input int ATRPeriod1 = {parse_int(params.get("ATRPeriod1", 20), 20)};
input double PriceEntryMult1 = {parse_float(params.get("PriceEntryMult1", 0.3), 0.3)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 2.0), 2.0)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 3.0), 3.0)};

input group "Session"
input int SignalFromHour = {parse_int(str(signal_from)[:2], 0)};
input int SignalFromMinute = {parse_int(str(signal_from)[3:], 0)};
input int SignalToHour = {parse_int(str(signal_to)[:2], 23)};
input int SignalToMinute = {parse_int(str(signal_to)[3:], 59)};
input int FridayFlatHour = {friday_flat_hour};
input int FridayFlatMinute = {friday_flat_minute};

datetime g_last_bar_time = 0;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;

int g_adx_handle = INVALID_HANDLE;
int g_sar_handle = INVALID_HANDLE;
int g_ichi_handle = INVALID_HANDLE;
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

bool IsFridayForceFlatTime(const datetime when)
{{
   MqlDateTime dt;
   TimeToStruct(when, dt);
   if(dt.day_of_week != 5)
      return false;
   int hhmm = dt.hour * 100 + dt.min;
   int exit_hhmm = FridayFlatHour * 100 + FridayFlatMinute;
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
      if(!OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      return true;
   }}
   return false;
}}

void CancelPendingOrders()
{{
   for(int idx = OrdersTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = OrderGetTicket(idx);
      if(!OrderSelect(ticket))
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((int)OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;
      trade.OrderDelete(ticket);
   }}
}}

void CloseAllPositions(string comment="")
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
   g_adx_handle = iADX(_Symbol, InpTimeframe, DIPeriod1);
   g_sar_handle = iSAR(_Symbol, InpTimeframe, SARStep, SARMax);
   g_ichi_handle = iIchimoku(_Symbol, InpTimeframe, 9, 26, 51);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod1);

   if(g_adx_handle == INVALID_HANDLE || g_sar_handle == INVALID_HANDLE || 
      g_ichi_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE)
   {{
      Print("Failed to create indicator handles");
      return INIT_FAILED;
   }}

   trade.SetExpertMagicNumber(InpMagicNumber);
   return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
   IndicatorRelease(g_adx_handle);
   IndicatorRelease(g_sar_handle);
   IndicatorRelease(g_ichi_handle);
   IndicatorRelease(g_atr_handle);
}}

void OnTick()
{{
   datetime now = TimeCurrent();

   if(HasOpenPosition())
   {{
      if(IsFridayForceFlatTime(now) || !InTimeWindow(now))
      {{
         CloseAllPositions("Session/Friday Exit");
         CancelPendingOrders();
         return;
      }}
   }}

   if(!IsNewBar()) return;

   // Logic at bar open
   if(g_long_expiry > 0 && now >= g_long_expiry) CancelPendingOrders();
   if(g_short_expiry > 0 && now >= g_short_expiry) CancelPendingOrders();

   if(HasOpenPosition() || HasPendingOrders()) return;
   if(!InTimeWindow(now) || IsFridayForceFlatTime(now)) return;

   double adx_plus, adx_minus, adx_plus_2, adx_plus_3, adx_plus_4, adx_plus_5;
   double adx_minus_2, adx_minus_3, adx_minus_4, adx_minus_5;
   double sar, ichi_kijun, atr, close, ichi_kijun_3, atr_3, atr_1;

   if(!CopyValue(g_adx_handle, 1, 0, adx_plus)) return;
   if(!CopyValue(g_adx_handle, 2, 0, adx_minus)) return;
   if(!CopyValue(g_adx_handle, 1, 2, adx_plus_2)) return;
   if(!CopyValue(g_adx_handle, 1, 3, adx_plus_3)) return;
   if(!CopyValue(g_adx_handle, 1, 4, adx_plus_4)) return;
   if(!CopyValue(g_adx_handle, 1, 5, adx_plus_5)) return;
   if(!CopyValue(g_adx_handle, 2, 2, adx_minus_2)) return;
   if(!CopyValue(g_adx_handle, 2, 3, adx_minus_3)) return;
   if(!CopyValue(g_adx_handle, 2, 4, adx_minus_4)) return;
   if(!CopyValue(g_adx_handle, 2, 5, adx_minus_5)) return;
   
   if(!CopyValue(g_sar_handle, 0, 0, sar)) return;
   if(!CopyValue(g_ichi_handle, 1, 0, ichi_kijun)) return;
   if(!CopyValue(g_ichi_handle, 1, 3, ichi_kijun_3)) return;
   if(!CopyValue(g_atr_handle, 0, 0, atr)) return;
   if(!CopyValue(g_atr_handle, 0, 3, atr_3)) return;
   if(!CopyValue(g_atr_handle, 0, 1, atr_1)) return;
   
   close = iClose(_Symbol, InpTimeframe, 0);

   if({long_condition})
   {{
      double entry_price = {"SymbolInfoDouble(_Symbol, SYMBOL_ASK)" if entry_style == "market_reclaim" else "ichi_kijun_3 + PriceEntryMult1 * atr_3"};
      double sl = entry_price - StopLossATR * atr_1;
      double tp = entry_price + ProfitTargetATR * atr_1;
      
      if("{entry_style}" == "market_reclaim")
      {{
         trade.Buy(InpLots, _Symbol, entry_price, sl, tp, "hk50_after_long");
      }}
      else
      {{
         trade.BuyStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "hk50_after_long");
         g_long_expiry = now + PeriodSeconds(InpTimeframe) * 8;
      }}
   }}
   else if({short_condition})
   {{
      double entry_price = {"SymbolInfoDouble(_Symbol, SYMBOL_BID)" if entry_style == "market_reclaim" else "ichi_kijun_3 - PriceEntryMult1 * atr_3"};
      double sl = entry_price + StopLossATR * atr_1;
      double tp = entry_price - ProfitTargetATR * atr_1;

      if("{entry_style}" == "market_reclaim")
      {{
         trade.Sell(InpLots, _Symbol, entry_price, sl, tp, "hk50_after_short");
      }}
      else
      {{
         trade.SellStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "hk50_after_short");
         g_short_expiry = now + PeriodSeconds(InpTimeframe) * 8;
      }}
   }}
}}
"""
