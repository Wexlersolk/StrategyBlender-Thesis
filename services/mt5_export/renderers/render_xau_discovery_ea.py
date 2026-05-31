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

def render_xau_discovery_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    entry = str(payload.get("entry_archetype", "breakout_stop"))
    volatility = str(payload.get("volatility_filter", "bb_width"))
    session_filter = str(payload.get("session_filter", "london_ny"))
    stop_model = str(payload.get("stop_model", "atr"))
    target_model = str(payload.get("target_model", "fixed_rr"))
    exit_model = str(payload.get("exit_model", "session_close"))
    symbol = str(payload.get("symbol", "XAUUSD"))
    direction_mode = str(payload.get("direction_mode", "both"))

    # Use signal_window_params to respect params.SignalTimeRangeFrom/To
    default_from_h, default_to_h = session_hours(session_filter)
    from_time, to_time = signal_window_params(
        symbol, params,
        default_from=f"{default_from_h:02d}:00",
        default_to=f"{default_to_h:02d}:00"
    )
    from_h, from_m = map(int, from_time.split(":"))
    to_h, to_m = map(int, to_time.split(":"))

    lot_val = normalized_export_lots(symbol, params, default=1.0, payload=payload)
    if "XAU" in symbol.upper():
        lot_val = lot_val / 100.0

    return f"""#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {mt5_timeframe(payload.get("timeframe", "H1"))};
input double InpLots = {lot_val};
input int InpMagicNumber = {magic_number(strategy_id)};

input group "Discovery Blocks"
input string InpEntryArchetype = "{entry}";
input string InpVolatilityFilter = "{volatility}";
input string InpSessionFilter = "{session_filter}";
input string InpStopModel = "{stop_model}";
input string InpTargetModel = "{target_model}";
input string InpExitModel = "{exit_model}";
input string InpDirectionMode = "{direction_mode}";

input group "Parameters"
input int HighestPeriod = {parse_int(params.get("HighestPeriod", 24), 24)};
input int LowestPeriod = {parse_int(params.get("LowestPeriod", 24), 24)};
input int ATRPeriod = {parse_int(params.get("ATRPeriod", 14), 14)};
input int FastEMA = {parse_int(params.get("FastEMA", 21), 21)};
input int SlowEMA = {parse_int(params.get("SlowEMA", 55), 55)};
input int RSIPeriod = {parse_int(params.get("RSIPeriod", 14), 14)};
input int BBWRPeriod = {parse_int(params.get("BBWRPeriod", 24), 24)};
input double BBWRMin = {parse_float(params.get("BBWRMin", 0.015), 0.015)};
input double EntryBufferATR = {parse_float(params.get("EntryBufferATR", 0.15), 0.15)};
input double StopLossATR = {parse_float(params.get("StopLossATR", 1.4), 1.4)};
input double ProfitTargetATR = {parse_float(params.get("ProfitTargetATR", 2.8), 2.8)};
input double TrailATR = {parse_float(params.get("TrailATR", 1.1), 1.1)};
input int ExitAfterBars = {parse_int(params.get("ExitAfterBars", 18), 18)};
input int PullbackLookback = {parse_int(params.get("PullbackLookback", 5), 5)};
input double PullbackATR = {parse_float(params.get("PullbackATR", 0.6), 0.6)};
input double ReclaimATR = {parse_float(params.get("ReclaimATR", 0.4), 0.4)};
input double BreakEvenATR = {parse_float(params.get("BreakEvenATR", 0.8), 0.8)};
input double TimeStopATR = {parse_float(params.get("TimeStopATR", 0.4), 0.4)};
input double MaxDistancePct = {parse_float(params.get("MaxDistancePct", 3.5), 3.5)};
input int ChopPeriod = {parse_int(params.get("ChopPeriod", 14), 14)};
input double ChopThreshold = {parse_float(params.get("ChopThreshold", 55.0), 55.0)};
input int VWAPPeriod = {parse_int(params.get("VWAPPeriod", 24), 24)};
input int QQERSIPeriod = {parse_int(params.get("QQERSIPeriod", 14), 14)};
input int QQESmoothPeriod = {parse_int(params.get("QQESmoothPeriod", 5), 5)};
input double QQEFactor = {parse_float(params.get("QQEFactor", 4.236), 4.236)};

input group "Session"
input int SignalFromHour = {from_h};
input int SignalFromMinute = {from_m};
input int SignalToHour = {to_h};
input int SignalToMinute = {to_m};

datetime g_last_bar_time = 0;
int g_ema_fast_handle = INVALID_HANDLE;
int g_ema_slow_handle = INVALID_HANDLE;
int g_atr_handle = INVALID_HANDLE;
int g_bands_handle = INVALID_HANDLE;
int g_rsi_handle = INVALID_HANDLE;
int g_ichi_handle = INVALID_HANDLE;
int g_vwap_handle = INVALID_HANDLE;
int g_qqe_rsi_handle = INVALID_HANDLE;
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


// --- Custom StrategyBlender Indicator Implementations ---

double WilderATR(const int period, const int shift)
{{
   double atr = 0.0;
   if(CopyValue(g_atr_handle, 0, shift, atr))
      return atr;
   
   // Fallback to custom calculation if handle is slow
   double tr_sum = 0;
   int start = shift + period * 10; // Increased warmup for Wilder convergence
   if(start >= iBars(_Symbol, InpTimeframe)) start = iBars(_Symbol, InpTimeframe) - 1;
   
   double prev_atr = 0;
   for(int i = start; i >= shift; i--)
   {{
      double h = iHigh(_Symbol, InpTimeframe, i);
      double l = iLow(_Symbol, InpTimeframe, i);
      double pc = iClose(_Symbol, InpTimeframe, i+1);
      double tr = MathMax(h-l, MathMax(MathAbs(h-pc), MathAbs(l-pc)));
      
      if(i == start) prev_atr = h - l;
      else prev_atr = ((prev_atr * (period - 1)) + tr) / period;
   }}
   return prev_atr;
}}


double SmaRSI(const int period, const int shift)
{{
   double up_sum = 0, dn_sum = 0;
   for(int i = 0; i < period; i++)
   {{
      double diff = iClose(_Symbol, InpTimeframe, shift + i) - iClose(_Symbol, InpTimeframe, shift + i + 1);
      if(diff > 0) up_sum += diff;
      else dn_sum += MathAbs(diff);
   }}
   if(up_sum + dn_sum == 0) return 50.0;
   return 100.0 * up_sum / (up_sum + dn_sum);
}}


void HeikenAshiValue(const int shift, double &ha_open, double &ha_close)
{{
   int depth = 150;
   int total_bars = iBars(_Symbol, InpTimeframe);
   if(shift + depth >= total_bars) depth = total_bars - shift - 1;
   
   double cur_ha_open = (iOpen(_Symbol, InpTimeframe, shift + depth) + iClose(_Symbol, InpTimeframe, shift + depth)) / 2.0;
   for(int i = shift + depth - 1; i >= shift; i--)
   {{
      double cur_ha_close = (iOpen(_Symbol, InpTimeframe, i) + iHigh(_Symbol, InpTimeframe, i) + iLow(_Symbol, InpTimeframe, i) + iClose(_Symbol, InpTimeframe, i)) / 4.0;
      if(i == shift)
      {{
         ha_open = cur_ha_open;
         ha_close = cur_ha_close;
         return;
      }}
      cur_ha_open = (cur_ha_open + cur_ha_close) / 2.0;
   }}
}}


double VWAPVariable(const int shift, const int period)
{{
   double sum_pv = 0.0;
   double sum_v = 0.0;
   for(int i = 0; i < period; ++i)
   {{
      double h = iHigh(_Symbol, InpTimeframe, shift + i);
      double l = iLow(_Symbol, InpTimeframe, shift + i);
      double c = iClose(_Symbol, InpTimeframe, shift + i);
      double o = iOpen(_Symbol, InpTimeframe, shift + i);
      double v = (double)iVolume(_Symbol, InpTimeframe, shift + i);
      sum_pv += ((h + l + c + o) / 4.0) * v;
      sum_v += v;
   }}
   return (sum_v == 0.0) ? 0.0 : sum_pv / sum_v;
}}


double QQEValue(const int shift)
{{
   double rsi_ma = 0.0;
   if(!CopyValue(g_qqe_rsi_handle, 0, shift, rsi_ma)) return 50.0;
   return rsi_ma;
}}


double IchimokuValue(const int shift, const int buffer)
{{
   double val = 0.0;
   if(!CopyValue(g_ichi_handle, buffer, shift, val)) return 0.0;
   return val;
}}


double ChopValue(const int shift)
{{
   double sum_atr = 0;
   for(int i=0; i < ChopPeriod; i++) sum_atr += WilderATR(1, shift + i);
   double highest = iHigh(_Symbol, InpTimeframe, iHighest(_Symbol, InpTimeframe, MODE_HIGH, ChopPeriod, shift));
   double lowest = iLow(_Symbol, InpTimeframe, iLowest(_Symbol, InpTimeframe, MODE_LOW, ChopPeriod, shift));
   double range = highest - lowest;
   if(range == 0) return 100.0;
   return 100.0 * MathLog10(sum_atr / range) / MathLog10((double)ChopPeriod);
}}

// -------------------------------------------------------


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
      return (hhmm >= from_hhmm && hhmm < to_hhmm);
   return (hhmm >= from_hhmm || hhmm < to_hhmm);
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
      if((type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_BUY_LIMIT) && StringFind(comment, "_long") >= 0 && g_long_expiry != 0 && bar_time >= g_long_expiry)
         trade.OrderDelete(ticket);
      if((type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_SELL_LIMIT) && StringFind(comment, "_short") >= 0 && g_short_expiry != 0 && bar_time >= g_short_expiry)
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
   double atr_now = WilderATR(ATRPeriod, 1);
   double sum = 0.0;
   for(int k = 1; k <= 48; k++)
      sum += WilderATR(ATRPeriod, k);
   double atr_mean = sum / 48.0;
   return atr_now >= (atr_mean * 1.05);
}}


bool VolatilityOk()
{{
   if(InpVolatilityFilter == "none")
      return true;
   if(InpVolatilityFilter == "atr_expansion")
      return AtrExpansionOk();
   if(InpVolatilityFilter == "session_impulse")
   {{
      double atr_1 = WilderATR(ATRPeriod, 1);
      return MathAbs(iClose(_Symbol, InpTimeframe, 1) - iOpen(_Symbol, InpTimeframe, 1)) >= (atr_1 * 0.75);
   }}
   if(InpVolatilityFilter == "choppiness_filter")
      return ChopValue(1) < ChopThreshold;
   return BollingerWidthRatio(1) >= BBWRMin;
}}


double TargetMultiple(const ENUM_POSITION_TYPE type)
{{
   if(InpTargetModel == "trend_runner")
      return ProfitTargetATR * 1.6;
   if(InpTargetModel == "atr_scaled")
      return ProfitTargetATR * 1.2;
   if(InpTargetModel == "asymmetric_runner")
      return (type == POSITION_TYPE_BUY) ? (ProfitTargetATR * 1.9) : (ProfitTargetATR * 1.4);
   return ProfitTargetATR;
}}


double LongStopPrice(const double entry_price, const double atr_value)
{{
   if(InpStopModel == "channel")
      return MathMin(LowestLow(LowestPeriod, 1), iOpen(_Symbol, InpTimeframe, 0) - atr_value * 0.5);
   if(InpStopModel == "swing")
      return LowestLow(PullbackLookback + 2, 1);
   if(InpStopModel == "atr_anchor")
   {{
      double ema_fast_1 = 0.0;
      CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1);
      return MathMin(ema_fast_1, LowestLow(LowestPeriod, 1)) - (atr_value * StopLossATR * 0.6);
   }}
   return entry_price - atr_value * StopLossATR;
}}


double ShortStopPrice(const double entry_price, const double atr_value)
{{
   if(InpStopModel == "channel")
      return MathMax(HighestHigh(HighestPeriod, 1), iOpen(_Symbol, InpTimeframe, 0) + atr_value * 0.5);
   if(InpStopModel == "swing")
      return HighestHigh(PullbackLookback + 2, 1);
   if(InpStopModel == "atr_anchor")
   {{
      double ema_fast_1 = 0.0;
      CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1);
      return MathMax(ema_fast_1, HighestHigh(HighestPeriod, 1)) + (atr_value * StopLossATR * 0.6);
   }}
   return entry_price + atr_value * StopLossATR;
}}


double LongTargetPrice(const double entry_price, const double atr_value)
{{
   return entry_price + atr_value * TargetMultiple(POSITION_TYPE_BUY);
}}


double ShortTargetPrice(const double entry_price, const double atr_value)
{{
   return entry_price - atr_value * TargetMultiple(POSITION_TYPE_SELL);
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
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
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
      double current_sl = PositionGetDouble(POSITION_SL);

      if(InpExitModel == "time_atr" && ExitAfterBars > 0)
      {{
         datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
         int bars_held = iBarShift(_Symbol, InpTimeframe, open_time);
         if(bars_held >= ExitAfterBars)
         {{
            trade.PositionClose(ticket);
            continue;
         }}
      }}

      // Trailing ATR Exit
      if(InpExitModel == "trailing_atr")
      {{
         double trail_dist = atr_value * TrailATR;
         double activation = atr_value; // Activation at 1.0 * ATR profit
         
         if(type == POSITION_TYPE_BUY)
         {{
            if(bid - entry > activation)
            {{
               double new_sl = bid - trail_dist;
               if(new_sl > current_sl || current_sl == 0)
                  trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), PositionGetDouble(POSITION_TP));
            }}
         }}
         else if(type == POSITION_TYPE_SELL)
         {{
            if(entry - ask > activation)
            {{
               double new_sl = ask + trail_dist;
               if(new_sl < current_sl || current_sl == 0)
                  trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), PositionGetDouble(POSITION_TP));
            }}
         }}
      }}

      // Break Even then Trail
      if(InpExitModel == "break_even_then_trail")
      {{
         double be_activation = atr_value * BreakEvenATR;
         double trail_dist = atr_value * TrailATR;
         
         if(type == POSITION_TYPE_BUY)
         {{
            if(bid - entry > be_activation)
            {{
               double new_sl = bid - trail_dist;
               if(new_sl > current_sl || current_sl == 0)
                  trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), PositionGetDouble(POSITION_TP));
            }}
         }}
         else if(type == POSITION_TYPE_SELL)
         {{
            if(entry - ask > be_activation)
            {{
               double new_sl = ask + trail_dist;
               if(new_sl < current_sl || current_sl == 0)
                  trade.PositionModify(ticket, NormalizeDouble(new_sl, _Digits), PositionGetDouble(POSITION_TP));
            }}
         }}
      }}

      if(InpExitModel == "channel_flip" || InpExitModel == "ema_flip")
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
      if(InpExitModel == "friday_flat")
      {{
         MqlDateTime dt;
         TimeCurrent(dt);
         if(dt.day_of_week == 5 && dt.hour >= 20)
            trade.PositionClose(ticket);
      }}
   }}
}}


bool LongSignalMarket(double &atr_value)
{{
   if(InpDirectionMode == "short_only") return false;

   double ema_fast_1 = 0.0, ema_fast_2 = 0.0, ema_slow_1 = 0.0;
   if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1))
      return false;
   if(!CopyValue(g_ema_fast_handle, 0, 2, ema_fast_2))
      return false;
   if(!CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
      return false;
      
   atr_value = WilderATR(ATRPeriod, 1);
   double rsi_1 = SmaRSI(RSIPeriod, 1);
   
   if(!VolatilityOk())
      return false;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double close_2 = iClose(_Symbol, InpTimeframe, 2);
   double open_1 = iOpen(_Symbol, InpTimeframe, 1);
   double low_1 = iLow(_Symbol, InpTimeframe, 1);
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
   if(InpEntryArchetype == "session_reclaim")
   {{
      return (
         low_1 < LowestLow(LowestPeriod, 1) &&
         close_1 > ema_fast_1 &&
         rsi_1 > 50.0
      );
   }}
   if(InpEntryArchetype == "range_fade_reclaim")
   {{
      return (
         close_1 > open_1 &&
         close_1 > (LowestLow(LowestPeriod, 1) + ReclaimATR * atr_value) &&
         rsi_1 < 45.0
      );
   }}
   if(InpEntryArchetype == "breakout_close")
      return close_1 > HighestHigh(HighestPeriod, 2);
   if(InpEntryArchetype == "heiken_reclaim")
   {{
      double ha_open_1, ha_close_1, ha_open_2, ha_close_2;
      HeikenAshiValue(1, ha_open_1, ha_close_1);
      HeikenAshiValue(2, ha_open_2, ha_close_2);
      return close_1 > ema_slow_1 && ha_close_1 > ha_open_1 && ha_close_2 <= ha_open_2;
   }}
   if(InpEntryArchetype == "ichimoku_momentum")
   {{
      double tenkan_1 = IchimokuValue(1, 0);
      double kijun_1 = IchimokuValue(1, 1);
      double tenkan_2 = IchimokuValue(2, 0);
      double kijun_2 = IchimokuValue(2, 1);
      return tenkan_1 > kijun_1 && close_1 > kijun_1 && tenkan_2 <= kijun_2;
   }}
   if(InpEntryArchetype == "vwap_pullback")
   {{
      double vwap_1 = VWAPVariable(1, VWAPPeriod);
      return close_1 > vwap_1 && low_1 <= vwap_1 + atr_value * PullbackATR && close_1 > ema_fast_1;
   }}
   if(InpEntryArchetype == "qqe_momentum")
   {{
      return QQEValue(1) > 50.0 && QQEValue(2) <= 50.0;
   }}
   return false;
}}


bool ShortSignalMarket(double &atr_value)
{{
   if(InpDirectionMode == "long_only") return false;

   double ema_fast_1 = 0.0, ema_fast_2 = 0.0, ema_slow_1 = 0.0;
   if(!CopyValue(g_ema_fast_handle, 0, 1, ema_fast_1))
      return false;
   if(!CopyValue(g_ema_fast_handle, 0, 2, ema_fast_2))
      return false;
   if(!CopyValue(g_ema_slow_handle, 0, 1, ema_slow_1))
      return false;

   atr_value = WilderATR(ATRPeriod, 1);
   double rsi_1 = SmaRSI(RSIPeriod, 1);

   if(!VolatilityOk())
      return false;

   double close_1 = iClose(_Symbol, InpTimeframe, 1);
   double close_2 = iClose(_Symbol, InpTimeframe, 2);
   double open_1 = iOpen(_Symbol, InpTimeframe, 1);
   double high_1 = iHigh(_Symbol, InpTimeframe, 1);
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
   if(InpEntryArchetype == "session_reclaim")
   {{
      return (
         high_1 > HighestHigh(HighestPeriod, 1) &&
         close_1 < ema_fast_1 &&
         rsi_1 < 50.0
      );
   }}
   if(InpEntryArchetype == "range_fade_reclaim")
   {{
      return (
         close_1 < open_1 &&
         close_1 < (HighestHigh(HighestPeriod, 1) - ReclaimATR * atr_value) &&
         rsi_1 > 55.0
      );
   }}
   if(InpEntryArchetype == "breakout_close")
      return close_1 < LowestLow(LowestPeriod, 2);
   if(InpEntryArchetype == "heiken_reclaim")
   {{
      double ha_open_1, ha_close_1, ha_open_2, ha_close_2;
      HeikenAshiValue(1, ha_open_1, ha_close_1);
      HeikenAshiValue(2, ha_open_2, ha_close_2);
      return close_1 < ema_slow_1 && ha_close_1 < ha_open_1 && ha_close_2 >= ha_open_2;
   }}
   if(InpEntryArchetype == "ichimoku_momentum")
   {{
      double tenkan_1 = IchimokuValue(1, 0);
      double kijun_1 = IchimokuValue(1, 1);
      double tenkan_2 = IchimokuValue(2, 0);
      double kijun_2 = IchimokuValue(2, 1);
      return tenkan_1 < kijun_1 && close_1 < kijun_1 && tenkan_2 >= kijun_2;
   }}
   if(InpEntryArchetype == "vwap_pullback")
   {{
      double vwap_1 = VWAPVariable(1, VWAPPeriod);
      return close_1 < vwap_1 && high_1 >= vwap_1 - atr_value * PullbackATR && close_1 < ema_fast_1;
   }}
   if(InpEntryArchetype == "qqe_momentum")
   {{
      return QQEValue(1) < 50.0 && QQEValue(2) >= 50.0;
   }}
   return false;
}}


bool LongSignalPending(double &atr_value, double &entry_price, double &sl, double &tp, ENUM_ORDER_TYPE &order_type)
{{
   if(InpDirectionMode == "short_only") return false;

   atr_value = WilderATR(ATRPeriod, 1);
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
      double highest_level = HighestHigh(HighestPeriod, 1);
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!(close_1 <= highest_level) || !DistanceOk(open_0, highest_level))
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
   if(InpDirectionMode == "long_only") return false;

   atr_value = WilderATR(ATRPeriod, 1);
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
      double lowest_level = LowestLow(LowestPeriod, 1);
      double close_1 = iClose(_Symbol, InpTimeframe, 1);
      if(!(close_1 >= lowest_level) || !DistanceOk(open_0, lowest_level))
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
      
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(stops_level <= 0) stops_level = point;

   if(order_type == ORDER_TYPE_BUY_STOP)
   {{
      if(entry_price <= ask + stops_level)
         return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
      return trade.BuyStop(InpLots, NormalizeDouble(entry_price, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
   }}
   if(order_type == ORDER_TYPE_BUY_LIMIT)
   {{
      if(entry_price >= ask - stops_level)
         return trade.Buy(InpLots, _Symbol, ask, sl, tp, "{strategy_id}_long");
      return trade.BuyLimit(InpLots, NormalizeDouble(entry_price, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_long");
   }}
   return false;
}}


bool PlaceShortEntry(const ENUM_ORDER_TYPE order_type, const double entry_price, const double sl, const double tp, const datetime expiry)
{{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0.0)
      return false;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double stops_level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(stops_level <= 0) stops_level = point;

   if(order_type == ORDER_TYPE_SELL_STOP)
   {{
      if(entry_price >= bid - stops_level)
         return trade.Sell(InpLots, _Symbol, bid, sl, tp, "{strategy_id}_short");
      return trade.SellStop(InpLots, NormalizeDouble(entry_price, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
   }}
   if(order_type == ORDER_TYPE_SELL_LIMIT)
   {{
      if(entry_price <= bid + stops_level)
         return trade.Sell(InpLots, _Symbol, bid, sl, tp, "{strategy_id}_short");
      return trade.SellLimit(InpLots, NormalizeDouble(entry_price, _Digits), _Symbol, sl, tp, ORDER_TIME_SPECIFIED, expiry, "{strategy_id}_short");
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
   g_rsi_handle = iRSI(_Symbol, InpTimeframe, RSIPeriod, PRICE_CLOSE);
   g_ichi_handle = iIchimoku(_Symbol, InpTimeframe, 9, 26, 52);
   g_qqe_rsi_handle = iMA(_Symbol, InpTimeframe, QQESmoothPeriod, 0, MODE_EMA, iRSI(_Symbol, InpTimeframe, QQERSIPeriod, PRICE_CLOSE));
   if(g_ema_fast_handle == INVALID_HANDLE || g_ema_slow_handle == INVALID_HANDLE || g_atr_handle == INVALID_HANDLE || g_bands_handle == INVALID_HANDLE || g_rsi_handle == INVALID_HANDLE || g_ichi_handle == INVALID_HANDLE || g_qqe_rsi_handle == INVALID_HANDLE)
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
   if(g_rsi_handle != INVALID_HANDLE)
      IndicatorRelease(g_rsi_handle);
   if(g_ichi_handle != INVALID_HANDLE)
      IndicatorRelease(g_ichi_handle);
   if(g_qqe_rsi_handle != INVALID_HANDLE)
      IndicatorRelease(g_qqe_rsi_handle);
}}


void OnTick()
{{
   // Exits are checked every tick for trailing/managed exits
   ApplyManagedExits();

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

   if(HasOpenPosition() || HasPendingOrders())
      return;

   double atr_value = 0.0;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return;

   if(InpEntryArchetype == "ema_reclaim" || InpEntryArchetype == "pullback_trend" || InpEntryArchetype == "breakout_close" || InpEntryArchetype == "session_reclaim" || InpEntryArchetype == "range_fade_reclaim" || InpEntryArchetype == "heiken_reclaim" || InpEntryArchetype == "ichimoku_momentum" || InpEntryArchetype == "vwap_pullback" || InpEntryArchetype == "qqe_momentum")
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
