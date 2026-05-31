from __future__ import annotations

from typing import Any
from services.mt5_export.utils import parse_float, parse_int, magic_number, session_hours, mql_broker_tradable_checks

def _render_xau_discovery_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    entry = str(payload.get("entry_archetype", "breakout_stop"))
    volatility = str(payload.get("volatility_filter", "bb_width"))
    session_filter = str(payload.get("session_filter", "london_ny"))
    stop_model = str(payload.get("stop_model", "atr"))
    target_model = str(payload.get("target_model", "fixed_rr"))
    exit_model = str(payload.get("exit_model", "session_close"))
    from_hour, to_hour = session_hours(session_filter)

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;
input double InpLots = { parse_float(params.get("mmLots", 1.0), 1.0) };
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Discovery Blocks"
input string InpEntryArchetype = "{entry}";
input string InpVolatilityFilter = "{volatility}";
input string InpSessionFilter = "{session_filter}";
input string InpStopModel = "{stop_model}";
input string InpTargetModel = "{target_model}";
input string InpExitModel = "{exit_model}";

input group "Parameters"
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 24), 24)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 24), 24)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int FastEMA = {parse_int(params.get("FastEMA", 21), 21)};
input int SlowEMA = {parse_int(params.get("SlowEMA", 55), 55)};
input int BBWRPeriod = {parse_int(params.get("BBWRPeriod", 24), 24)};
input double BBWRMin = {parse_float(params.get("BBWRMin", 0.015), 0.015)};
input double EntryBufferATR = {parse_float(params.get("EntryBufferATR", 0.15), 0.15)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 1.4), 1.4)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 2.8), 2.8)};
input double TrailATR = {parse_float(params.get("TrailATR", 1.1), 1.1)};
input int ExitAfterBars = {parse_int(params.get("ExitAfterBars", 18), 18)};
input int PullbackLookback = {parse_int(params.get("PullbackLookback", 5), 5)};
input double PullbackATR = {parse_float(params.get("PullbackATR", 0.6), 0.6)};
input double BreakEvenATR = {parse_float(params.get("BreakEvenATR", 0.8), 0.8)};
input double TimeStopATR = {parse_float(params.get("TimeStopATR", 0.4), 0.4)};
input double MaxDistancePct = {parse_float(params.get("MaxDistancePct", 3.5), 3.5)};

input group "Session"
input int SignalFromHour = {{from_hour}};
input int SignalFromMinute = 0;
input int SignalToHour = {{to_hour}};
input int SignalToMinute = 0;

datetime g_last_bar_time = 0;
int g_ema_fast_handle = INVALID_HANDLE;
int g_ema_slow_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
int g_bands_handle = INVALID_HANDLE;
datetime g_long_expiry = 0;
datetime g_short_expiry = 0;


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
{_mql_broker_tradable_checks("XAUUSD")}
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
      if((type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_BUY_LIMIT) && comment == "{strategy_id}_long" && g_long_expiry != 0 && bar_time >= g_long_expiry)
         trade.OrderDelete(ticket);
      if((type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_SELL_LIMIT) && comment == "{strategy_id}_short" && g_short_expiry != 0 && bar_time >= g_short_expiry)
         trade.OrderDelete(ticket);
   }}
}}


double LowestLow(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double low = iLow(_Symbol, InpTimeframe, shift);
      if(low == 0.0)
         continue;
      value = MathMin(value, low);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}


double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double high = iHigh(_Symbol, InpTimeframe, shift);
      if(high == 0.0)
         continue;
      value = MathMax(value, high);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}


double BollingerWidthRatio(const int shift)
{{
   double middle = 0.0;
   double upper = 0.0;
   double lower = 0.0;
   if(!CopyValue(g_bands_handle, 0, shift, middle))
      return 0.0;
   if(!CopyValue(g_bands_handle, 1, shift, upper))
      return 0.0;
   if(!CopyValue(g_bands_handle, 2, shift, lower))
      return 0.0;
   if(MathAbs(middle) < 1e-9)
      return 0.0;
   return ((upper - lower) / middle) * 100.0;
}}


bool AtrExpansionOk()
{{
   double atr_values[];
   ArraySetAsSeries(atr_values, true);
   int copied = CopyBuffer(g_atr_handle, 0, 1, 48, atr_values);
   if(copied < 12)
      return false;
   double atr_now = atr_values[0];
   double sum = 0.0;
   for(int i = 0; i < copied; ++i)
      sum += atr_values[i];
   double atr_mean = sum / copied;
   return atr_now >= (atr_mean * 1.05);
}}


bool VolatilityOk()
{{
   if(InpVolatilityFilter == "none")
      return true;
   if(InpVolatilityFilter == "atr_expansion")
      return AtrExpansionOk();
   return BollingerWidthRatio(1) >= BBWRMin;
}}


double TargetMultiple()
{{
   if(InpTargetModel == "trend_runner")
      return ProfitTargetATR * 1.6;
   if(InpTargetModel == "atr_scaled")
      return ProfitTargetATR * 1.2;
   return ProfitTargetATR;
}}


double LongStopPrice(const double entry_price, const double atr_value)
{{
   if(InpStopModel == "channel")
      return MathMin(LowestLow(LowestPeriod, 2), entry_price - atr_value * 0.5);
   if(InpStopModel == "swing")
      return LowestLow(PullbackLookback + 2, 2);
   return entry_price - atr_value * StopLossATR;
}}


double ShortStopPrice(const double entry_price, const double atr_value)
{{
   if(InpStopModel == "channel")
      return MathMax(HighestHigh(HighestPeriod, 2), entry_price + atr_value * 0.5);
   if(InpStopModel == "swing")
      return HighestHigh(PullbackLookback + 2, 2);
   return entry_price + atr_value * StopLossATR;
}}


double LongTargetPrice(const double entry_price, const double atr_value)
{{
   return entry_price + atr_value * TargetMultiple();
}}


double ShortTargetPrice(const double entry_price, const double atr_value)
{{
   return entry_price - atr_value * TargetMultiple();
}}


bool DistanceOk(const double current_open, const double ref_price)
{{
   if(current_open <= 0.0)
      return false;
   return (MathAbs(current_open - ref_price) / current_open * 100.0) <= MaxDistancePct;
}}


void ApplyManagedExits()
{{
   double current_close = iClose(_Symbol, InpTimeframe, 0);
   double ema_fast = 0.0;
   double atr_value = 0.0;
   CopyValue(g_ema_fast_handle, 0, 0, ema_fast);
   CopyValue(g_atr_handle, 0, 1, atr_value);

   for(int idx = PositionsTotal() - 1; idx >= 0; --idx)
   {{
      ulong ticket = PositionGetTicket(idx);
      if(!PositionSelectByTicket(ticket))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);

      if(InpExitModel == "channel_flip")
      {{
         if(type == POSITION_TYPE_BUY && current_close < ema_fast)
            trade.PositionClose(ticket);
         if(type == POSITION_TYPE_SELL && current_close > ema_fast)
            trade.PositionClose(ticket);
      }}
      if(InpExitModel == "atr_time_stop")
      {{
         if(type == POSITION_TYPE_BUY && (entry - current_close) > atr_value * TimeStopATR)
            trade.PositionClose(ticket);
         if(type == POSITION_TYPE_SELL && (current_close - entry) > atr_value * TimeStopATR)
            trade.PositionClose(ticket);
      }}
   }}
}}


bool LongSignalMarket(double &atr_value)
{{
   double ema_fast_1 = 0.0, ema_fast_2 = 0.0, ema_slow_1 = 0.0;
   if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1))
      return false;
   if(!CopyValue(g_ema_fast_handle, 0, 2, ema_fast_2))
      return false;
   if(!CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
      return false;
   if(!CopyValue(g_atr_handle, 0, 1, atr_value))
      return false;
   if(!VolatilityOk())
      return false;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double close_2 = iClose(_Symbol, InpTimeframe, 2);
   double open_1 = iOpen(_Symbol, InpTimeframe, 1);
   if(close_1 <= 0.0 || open_1 <= 0.0)
      return false;
   if(!DistanceOk(iOpen(_Symbol, InpTimeframe, 0), close_1))
      return false;

   if(InpEntryArchetype == "ema_reclaim")
   {{
      return (
         close_1 > ema_slow_1 &&
         LowestLow(PullbackLookback, 1) < ema_fast_1 &&
         close_1 > ema_fast_1 &&
         close_2 <= ema_fast_2
      );
   }}
   if(InpEntryArchetype == "pullback_trend")
   {{
      return (
         close_1 > ema_slow_1 &&
         LowestLow(PullbackLookback, 1) <= ema_fast_1 &&
         close_1 > ema_fast_1
      );
   }}
   if(InpEntryArchetype == "breakout_close")
      return close_1 > HighestHigh(HighestPeriod, 2);
   return false;
}}


bool ShortSignalMarket(double &atr_value)
{{
   double ema_fast_1 = 0.0, ema_fast_2 = 0.0, ema_slow_1 = 0.0;
   if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1))
      return false;
   if(!CopyValue(g_ema_fast_handle, 0, 2, ema_fast_2))
      return false;
   if(!CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
      return false;
   if(!CopyValue(g_atr_handle, 0, 1, atr_value))
      return false;
   if(!VolatilityOk())
      return false;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double close_2 = iClose(_Symbol, InpTimeframe, 2);
   double open_1 = iOpen(_Symbol, InpTimeframe, 1);
   if(close_1 <= 0.0 || open_1 <= 0.0)
      return false;
   if(!DistanceOk(iOpen(_Symbol, InpTimeframe, 0), close_1))
      return false;

   if(InpEntryArchetype == "ema_reclaim")
   {{
      return (
         close_1 < ema_slow_1 &&
         HighestHigh(PullbackLookback, 1) > ema_fast_1 &&
         close_1 < ema_fast_1 &&
         close_2 >= ema_fast_2
      );
   }}
   if(InpEntryArchetype == "pullback_trend")
   {{
      return (
         close_1 < ema_slow_1 &&
         HighestHigh(PullbackLookback, 1) >= ema_fast_1 &&
         close_1 < ema_fast_1
      );
   }}
   if(InpEntryArchetype == "breakout_close")
      return close_1 < LowestLow(LowestPeriod, 2);
   return false;
}}


bool LongSignalPending(double &atr_value, double &entry_price, double &sl, double &tp, ENUM_ORDER_TYPE &order_type)
{{
   if(!CopyValue(g_atr_handle, 0, 1, atr_value))
      return false;
   if(!VolatilityOk())
      return false;
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   if(open_0 <= 0.0)
      return false;

   if(InpEntryArchetype == "atr_pullback_limit")
   {{
      double ema_fast_1 = 0.0, ema_slow_1 = 0.0, close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1) || !CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
         return false;
      if(!(close_1 > ema_slow_1 && close_1 > ema_fast_1))
         return false;
      if(!DistanceOk(open_0, close_1))
         return false;
      entry_price = ema_fast_1 - (atr_value * PullbackATR);
      sl = LongStopPrice(entry_price, atr_value);
      tp = LongTargetPrice(entry_price, atr_value);
      order_type = ORDER_TYPE_BUY_LIMIT;
      return true;
   }}

   if(InpEntryArchetype == "breakout_stop")
   {{
      double highest_level = HighestHigh(HighestPeriod, 2);
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!(close_1 > highest_level) || !DistanceOk(open_0, highest_level))
         return false;
      entry_price = highest_level + (atr_value * EntryBufferATR);
      sl = LongStopPrice(entry_price, atr_value);
      tp = LongTargetPrice(entry_price, atr_value);
      order_type = ORDER_TYPE_BUY_STOP;
      return true;
   }}

   return false;
}}


bool ShortSignalPending(double &atr_value, double &entry_price, double &sl, double &tp, ENUM_ORDER_TYPE &order_type)
{{
   if(!CopyValue(g_atr_handle, 0, 1, atr_value))
      return false;
   if(!VolatilityOk())
      return false;
   double open_0 = iOpen(_Symbol, InpTimeframe, 0);
   if(open_0 <= 0.0)
      return false;

   if(InpEntryArchetype == "atr_pullback_limit")
   {{
      double ema_fast_1 = 0.0, ema_slow_1 = 0.0, close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1) || !CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
         return false;
      if(!(close_1 < ema_slow_1 && close_1 < ema_fast_1))
         return false;
      if(!DistanceOk(open_0, close_1))
         return false;
      entry_price = ema_fast_1 + (atr_value * PullbackATR);
      sl = ShortStopPrice(entry_price, atr_value);
      tp = ShortTargetPrice(entry_price, atr_value);
      order_type = ORDER_TYPE_SELL_LIMIT;
      return true;
   }}

   if(InpEntryArchetype == "breakout_stop")
   {{
      double lowest_level = LowestLow(LowestPeriod, 2);
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!(close_1 < lowest_level) || !DistanceOk(open_0, lowest_level))
         return false;
      entry_price = lowest_level - (atr_value * EntryBufferATR);
      sl = ShortStopPrice(entry_price, atr_value);
      tp = ShortTargetPrice(entry_price, atr_value);
      order_type = ORDER_TYPE_SELL_STOP;
      return true;
   }}

   return false;
}}


bool PlaceLongEntry(const ENUM_ORDER_TYPE order_type, const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask <= 0.0)
      return false;
   if(order_type == ORDER_TYPE_BUY_STOP)
   {{
      if(entry_price <= ask)
         return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
      return trade.BuyStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
   }}
   if(order_type == ORDER_TYPE_BUY_LIMIT)
   {{
      if(entry_price >= ask)
         return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
      return trade.BuyLimit(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
   }}
   return false;
}}


bool PlaceShortEntry(const ENUM_ORDER_TYPE order_type, const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;
   if(order_type == ORDER_TYPE_SELL_STOP)
   {{
      if(entry_price >= bid)
         return trade.Sell(InpLots, _Symbol, bid, sl, tp, "{strategy_id}_short");
      return trade.SellStop(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
   }}
   if(order_type == ORDER_TYPE_SELL_LIMIT)
   {{
      if(entry_price <= bid)
         return trade.Sell(InpLots, _Symbol, bid, sl, tp, "{strategy_id}_short");
      return trade.SellLimit(InpLots, entry_price, _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
   }}
   return false;
}}


int OnInit()
{{
   trade.SetExpertMagicNumber(InpMagicNumber);
   g_ema_fast_handle = iMA(_Symbol, InpTimeframe, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_ema_slow_handle = iMA(_Symbol, InpTimeframe, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_atr_handle = iATR(_Symbol, InpTimeframe, ATRPeriod);
   g_bands_handle = iBands(_Symbol, InpTimeframe, BBWRPeriod, 0, 2.0, PRICE_CLOSE);
   if(g_ema_fast_handle == INVALID_HANDLE || g_ema_slow_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE || g_bands_handle == INVALID_HANDLE)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}}


void OnDeinit(const int reason)
{{
   if(g_ema_fast_handle != INVALID_HANDLE)
      IndicatorRelease(g_ema_fast_handle);
   if(g_ema_slow_handle != INVALID_HANDLE)
      IndicatorRelease(g_ema_slow_handle);
   if(g_atr_handle != INVALID_HANDLE)
      IndicatorRelease(g_atr_handle);
   if(g_bands_handle != INVALID_HANDLE)
      IndicatorRelease(g_bands_handle);
}}


void OnTick()
{{
   if(!IsNewBar())
      return;

   datetime bar_time = iTime(_Symbol, InpTimeframe, 0);
   bool session_ok = InTimeWindow(bar_time);

   CancelExpiredOrders(bar_time);

   if(!session_ok)
   {{
      CloseManagedPositions();
      CancelManagedOrders();
      return;
   }}

   ApplyManagedExits();

   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr_value = 0.0;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return;

   if(InpEntryArchetype == "ema_reclaim" || InpEntryArchetype == "pullback_trend" || InpEntryArchetype == "breakout_close")
   {{
      if(LongSignalMarket(atr_value))
      {{
         double sl = LongStopPrice(ask, atr_value);
         double tp = LongTargetPrice(ask, atr_value);
         trade.Buy(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_long");
         return;
      }}
      if(ShortSignalMarket(atr_value))
      {{
         double sl = ShortStopPrice(bid, atr_value);
         double tp = ShortTargetPrice(bid, atr_value);
         trade.Sell(InpLots, _Symbol, 0.0, sl, tp, "{strategy_id}_short");
         return;
      }}
      return;
   }}

   double entry_price = 0.0, sl = 0.0, tp = 0.0;
   ENUM_ORDER_TYPE order_type;
   datetime expiry = bar_time + PeriodSeconds(InpTimeframe) * 3;
   if(LongSignalPending(atr_value, entry_price, sl, tp, order_type))
   {{
      if(PlaceLongEntry(order_type, entry_price, sl, tp, expiry))
         g_long_expiry = expiry;
      return;
   }}

   if(ShortSignalPending(atr_value, entry_price, sl, tp, order_type))
   {{
      if(PlaceShortEntry(order_type, entry_price, sl, tp, expiry))
         g_short_expiry = expiry;
   }}
}}
"""
