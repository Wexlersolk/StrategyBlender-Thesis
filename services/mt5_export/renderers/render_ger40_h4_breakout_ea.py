from __future__ import annotations
from typing import Any
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    magic_number,
    mt5_timeframe,
    normalized_export_lots,
)

def render_ger40_h4_breakout_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    params = dict(payload.get("params", {}))
    symbol = str(payload.get("symbol", "GER40.CASH"))
    mql_tf = mt5_timeframe(payload.get("timeframe", "H4"))
    direction_mode = str(payload.get("direction_mode", "both")).lower()
    
    source = """#property strict
#property version   "1.00"
#property description "GER40 H4 Breakout EA - {STRATEGY_ID}"
#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {MQL_TF};
input double InpLots = {LOTS};
input int InpMagicNumber = {MAGIC};

input group "Breakout"
input int HighestPeriod = {HIGHEST_PERIOD};
input int LowestPeriod = {LOWEST_PERIOD};
input int EMAPeriod = {EMA_PERIOD};
input int ATRPeriod = {ATR_PERIOD};

input group "Filters"
input int UseSlowEMA = {USE_SLOW_EMA};
input int UseSqueeze = {USE_SQUEEZE};
input double ADXMin = {ADX_MIN};
input int ADXPeriod = {ADX_PERIOD};

input group "Entry"
input double StopLossATR = {SL_ATR};
input double ProfitTargetATR = {TP_ATR};
input double EntryBufferATR = {ENTRY_BUFFER};

input group "Session"
input string InpSessionFrom = "{SESSION_FROM}";
input string InpSessionTo = "{SESSION_TO}";

// Global handles
int g_hEMA, g_hATR, g_hADX, g_hStdDev;
datetime g_last_bar_time = 0;

int OnInit()
{{
    Print("Initializing EA for ", _Symbol);
    g_hEMA = iMA(_Symbol, InpTimeframe, EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
    g_hATR = iATR(_Symbol, InpTimeframe, ATRPeriod);
    g_hADX = iADX(_Symbol, InpTimeframe, ADXPeriod);
    g_hStdDev = iStdDev(_Symbol, InpTimeframe, 20, 0, MODE_SMA, PRICE_CLOSE);

    if(g_hEMA == INVALID_HANDLE || g_hATR == INVALID_HANDLE || g_hADX == INVALID_HANDLE || g_hStdDev == INVALID_HANDLE)
    {{
        Print("Failed to create indicator handles");
        return INIT_FAILED;
    }}

    trade.SetExpertMagicNumber(InpMagicNumber);
    return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
    IndicatorRelease(g_hEMA);
    IndicatorRelease(g_hATR);
    IndicatorRelease(g_hADX);
    IndicatorRelease(g_hStdDev);
}}

bool IsNewBar()
{{
    datetime current = iTime(_Symbol, InpTimeframe, 0);
    if(current != g_last_bar_time)
    {{
        g_last_bar_time = current;
        return true;
    }}
    return false;
}}

bool IsInSession()
{{
    MqlDateTime dt;
    TimeCurrent(dt);
    int now_min = dt.hour * 60 + dt.min;
    
    int from_h, from_m, to_h, to_m;
    string parts[];
    StringSplit(InpSessionFrom, ':', parts);
    from_h = (int)StringToInteger(parts[0]);
    from_m = (int)StringToInteger(parts[1]);
    
    StringSplit(InpSessionTo, ':', parts);
    to_h = (int)StringToInteger(parts[0]);
    to_m = (int)StringToInteger(parts[1]);
    
    int start = from_h * 60 + from_m;
    int end = to_h * 60 + to_m;
    
    if(start <= end) return (now_min >= start && now_min <= end);
    else return (now_min >= start || now_min <= end);
}}

double GetVal(int handle, int buffer=0, int shift=1)
{{
    double val[1];
    if(CopyBuffer(handle, buffer, shift, 1, val) < 1) return 0;
    return val[0];
}}

double HighestHigh(const int lookback, const int start_shift)
{{
   double value = -DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iHigh(_Symbol, InpTimeframe, shift);
      if(x != 0.0) value = MathMax(value, x);
   }}
   return (value == -DBL_MAX) ? 0.0 : value;
}}

double LowestLow(const int lookback, const int start_shift)
{{
   double value = DBL_MAX;
   for(int shift = start_shift; shift < start_shift + lookback; ++shift)
   {{
      double x = iLow(_Symbol, InpTimeframe, shift);
      if(x != 0.0) value = MathMin(value, x);
   }}
   return (value == DBL_MAX) ? 0.0 : value;
}}

void OnTick()
{{
    if(!IsNewBar()) return;
    Print("Processing Bar: ", TimeToString(iTime(_Symbol, InpTimeframe, 0)));
    
    MqlDateTime dt;
    TimeCurrent(dt);
    // Friday close (approx 20:00)
    if(dt.day_of_week == 5 && dt.hour >= 20) {{
        CloseAll();
        return;
    }}
    
    if(PositionsTotal() > 0) return;
    if(!IsInSession()) return;

    double close_1 = iClose(_Symbol, InpTimeframe, 1);
    double ema_1 = GetVal(g_hEMA);
    double atr_1 = GetVal(g_hATR);
    double adx_1 = GetVal(g_hADX);
    
    // Squeeze logic
    double stddevs[50];
    double closes[50];
    double bbwr_sum = 0;
    int k_count = 0;
    if(CopyBuffer(g_hStdDev, 0, 1, 50, stddevs) == 50 && CopyClose(_Symbol, InpTimeframe, 1, 50, closes) == 50)
    {{
        for(int k=0; k<50; k++) {{
            if(closes[k] > 0) {{
               bbwr_sum += (stddevs[k] * 4.0 / closes[k]) * 100.0;
               k_count++;
            }}
        }}
    }}
    double bbwr_avg = (k_count > 0) ? (bbwr_sum / k_count) : 0;
    double bbwr = (close_1 > 0) ? (GetVal(g_hStdDev) * 4.0 / close_1 * 100.0) : 0;

    bool trend_long = (UseSlowEMA == 0) || (close_1 > ema_1);
    bool trend_short = (UseSlowEMA == 0) || (close_1 < ema_1);
    bool adx_ok = (adx_1 >= ADXMin);
    bool squeeze_ok = (UseSqueeze == 0) || (bbwr < bbwr_avg);

    // Breakout levels
    double hh = HighestHigh(HighestPeriod, 2);
    double ll = LowestLow(LowestPeriod, 2);
    Print("Levels: HH=", hh, " LL=", ll, " Close=", close_1, " EMA=", ema_1, " ADX=", adx_1, " BBWR=", bbwr);
    double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

    if(("{DIR_MODE}" != "short_only") && trend_long && adx_ok && squeeze_ok && (close_1 > hh + 0.2 * _Point))
    {{
        Print("Sending Buy Order...");
        double open_0 = iOpen(_Symbol, InpTimeframe, 0);
        double sl = NormalizeDouble(open_0 - StopLossATR * atr_1, _Digits);
        double tp = NormalizeDouble(open_0 + ProfitTargetATR * atr_1, _Digits);
        trade.Buy(InpLots, _Symbol, 0, sl, tp, "{STRATEGY_ID}_long");
    }}
    else if(("{DIR_MODE}" != "long_only") && trend_short && adx_ok && squeeze_ok && (close_1 < ll - 0.2 * _Point))
    {{
        Print("Sending Sell Order...");
        double open_0 = iOpen(_Symbol, InpTimeframe, 0);
        double sl = NormalizeDouble(open_0 + StopLossATR * atr_1, _Digits);
        double tp = NormalizeDouble(open_0 - ProfitTargetATR * atr_1, _Digits);
        trade.Sell(InpLots, _Symbol, 0, sl, tp, "{STRATEGY_ID}_short");
    }}
}}

void CloseAll()
{{
    for(int i=PositionsTotal()-1; i>=0; i--)
    {{
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
        {{
            if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
                trade.PositionClose(ticket);
        }}
    }}
}}
"""
    return source.format(
        STRATEGY_ID=strategy_id,
        MQL_TF=mql_tf,
        LOTS=normalized_export_lots(symbol, params, default=1.0, payload=payload),
        MAGIC=magic_number(strategy_id),
        HIGHEST_PERIOD=parse_int(params.get("HighestPeriod", 60), 60),
        LOWEST_PERIOD=parse_int(params.get("LowestPeriod", 24), 24),
        EMA_PERIOD=parse_int(params.get("SlowEMA", 200), 200),
        ATR_PERIOD=parse_int(params.get("ATRPeriod", 14), 14),
        USE_SLOW_EMA=parse_int(params.get("UseSlowEMA", 1), 1),
        USE_SQUEEZE=parse_int(params.get("UseSqueeze", 0), 0),
        ADX_MIN=parse_float(params.get("ADXMin", 20.0), 20.0),
        ADX_PERIOD=parse_int(params.get("ADXPeriod", 14), 14),
        SL_ATR=parse_float(params.get("StopLossATR", 3.0), 3.0),
        TP_ATR=parse_float(params.get("ProfitTargetATR", 6.0), 6.0),
        ENTRY_BUFFER=parse_float(params.get("EntryBufferATR", 0.1), 0.1),
        SESSION_FROM=params.get("SignalTimeRangeFrom", "13:30" if params.get("session_filter") == "ny_only" else "00:00"),
        SESSION_TO=params.get("SignalTimeRangeTo", "20:00" if params.get("session_filter") == "ny_only" else "23:59"),
        DIR_MODE=direction_mode,
    )
