from __future__ import annotations
from typing import Any
from services.mt5_export.utils import (
    parse_int,
    parse_float,
    magic_number,
    mt5_timeframe,
    normalized_export_lots,
)

def render_ger40_specialist_ea(strategy_id: str, payload: dict[str, Any]) -> str:
    from services.mt5_export.utils import (
        parse_int,
        parse_float,
        magic_number,
        mt5_timeframe,
        normalized_export_lots,
    )
    
    params = dict(payload.get("params", {}))
    symbol = str(payload.get("symbol", "GER40.CASH"))
    mql_tf = mt5_timeframe(payload.get("timeframe", "M15"))
    
    archetype = str(payload.get("archetype", "ema_pullback"))
    session_filter = str(payload.get("session_filter", "london_morning"))
    
    session_windows = {
        "london_morning": ("07:00", "10:00"),
        "london_only": ("07:00", "11:00"),
        "ny_only": ("13:30", "17:30"),
        "london_ny": ("07:00", "17:30"),
        "all_day": ("00:00", "23:59"),
    }
    session_from, session_to = session_windows.get(session_filter, ("07:00", "10:00"))

    source = """#property strict
#property version   "1.00"
#property description "GER40 Specialist EA - {STRATEGY_ID}"
#property strict

#include <Trade/Trade.mqh>

CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpTimeframe = {MQL_TF};
input double InpLots = {LOTS};
input int InpMagicNumber = {MAGIC};

input group "Filters"
input int InpFastEMA = {FAST_EMA};
input int InpSlowEMA = {SLOW_EMA};
input int InpADXPeriod = {ADX_PERIOD};
input double InpADXMin = {ADX_MIN};
input int InpRSIPeriod = {RSI_PERIOD};
input double InpRSILongMin = {RSI_LONG_MIN};
input double InpRSIShortMax = {RSI_SHORT_MAX};
input int InpBBWRPeriod = {BBWR_PERIOD};

input group "Entry"
input double InpStopLossATR = {SL_ATR};
input double InpProfitTargetATR = {TP_ATR};
input double InpTrailATR = {TRAIL_ATR};
input double InpBreakEvenATR = {BE_ATR};
input int InpATRPeriod = {ATR_PERIOD};

input group "Session"
input string InpSessionFrom = "{SESSION_FROM}";
input string InpSessionTo = "{SESSION_TO}";

// Global handles
int g_hFastEMA, g_hSlowEMA, g_hADX, g_hRSI, g_hATR, g_hStdDev;
datetime g_last_bar_time = 0;

int OnInit()
{{
    g_hFastEMA = iMA(_Symbol, InpTimeframe, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
    g_hSlowEMA = iMA(_Symbol, InpTimeframe, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
    g_hADX = iADX(_Symbol, InpTimeframe, InpADXPeriod);
    g_hRSI = iRSI(_Symbol, InpTimeframe, InpRSIPeriod, PRICE_CLOSE);
    g_hATR = iATR(_Symbol, InpTimeframe, InpATRPeriod);
    g_hStdDev = iStdDev(_Symbol, InpTimeframe, InpBBWRPeriod, 0, MODE_SMA, PRICE_CLOSE);

    if(g_hFastEMA == INVALID_HANDLE || g_hSlowEMA == INVALID_HANDLE || 
       g_hADX == INVALID_HANDLE || g_hRSI == INVALID_HANDLE || 
       g_hATR == INVALID_HANDLE || g_hStdDev == INVALID_HANDLE)
        return INIT_FAILED;

    trade.SetExpertMagicNumber(InpMagicNumber);
    return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason)
{{
    IndicatorRelease(g_hFastEMA);
    IndicatorRelease(g_hSlowEMA);
    IndicatorRelease(g_hADX);
    IndicatorRelease(g_hRSI);
    IndicatorRelease(g_hATR);
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

void OnTick()
{{
    if(!IsNewBar()) return;
    
    ManagePositions();

    MqlDateTime dt;
    TimeCurrent(dt);
    // Friday close (approx 20:00)
    if(dt.day_of_week == 5 && dt.hour >= 20) {{
        CloseAll();
        return;
    }}
    
    // Safety exit
    if(!IsInSession()) {{
        CloseAll();
        return;
    }}
    
    if(PositionsTotal() > 0) return;

    double close = iClose(_Symbol, InpTimeframe, 1);
    double fast = GetVal(g_hFastEMA);
    double slow = GetVal(g_hSlowEMA);
    double adx = GetVal(g_hADX);
    double rsi = GetVal(g_hRSI);
    double atr = GetVal(g_hATR);
    
    // Bollinger Band Width Ratio logic (Matching Python implementation)
    double stddevs[50];
    double closes[50];
    double bbwr_sum = 0;
    int k_count = 0;
    if(CopyBuffer(g_hStdDev, 0, 1, 50, stddevs) == 50 && CopyClose(_Symbol, InpTimeframe, 1, 50, closes) == 50)
    {{
        for(int k=0; k<50; k++) {{
            if(closes[k] > 0) {{
               // Python bbwr = ((upper - lower) / mid) * 100.0
               // (upper - lower) = 2 * dev * stddev = 4.0 * stddev
               bbwr_sum += (stddevs[k] * 4.0 / closes[k]) * 100.0;
               k_count++;
            }}
        }}
    }}
    double bbwr_avg = (k_count > 0) ? (bbwr_sum / k_count) : 0;
    double bbwr = (close > 0) ? (GetVal(g_hStdDev) * 4.0 / close * 100.0) : 0;

    bool trend_up = (close > slow);
    bool trend_dn = (close < slow);
    bool strong = (adx > InpADXMin);
    bool squeeze_ok = (bbwr > bbwr_avg);
    
    // EMA Pullback logic
    double low5 = iLow(_Symbol, InpTimeframe, iLowest(_Symbol, InpTimeframe, MODE_LOW, 5, 1));
    double high5 = iHigh(_Symbol, InpTimeframe, iHighest(_Symbol, InpTimeframe, MODE_HIGH, 5, 1));
    
    if(trend_up && strong && squeeze_ok && rsi > InpRSILongMin)
    {{
        if(low5 <= fast && close > fast)
        {{
            double sl = close - InpStopLossATR * atr;
            double tp = close + InpProfitTargetATR * atr;
            trade.Buy(InpLots, _Symbol, 0, sl, tp, "{STRATEGY_ID}");
        }}
    }}
    else if(trend_dn && strong && squeeze_ok && rsi < InpRSIShortMax)
    {{
        if(high5 >= fast && close < fast)
        {{
            double sl = close + InpStopLossATR * atr;
            double tp = close - InpProfitTargetATR * atr;
            trade.Sell(InpLots, _Symbol, 0, sl, tp, "{STRATEGY_ID}");
        }}
    }}
}}

void ManagePositions()
{{
    for(int i=PositionsTotal()-1; i>=0; i--)
    {{
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
        {{
            if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
            
            double atr = GetVal(g_hATR);
            double price = PositionGetDouble(POSITION_PRICE_OPEN);
            double current = PositionGetDouble(POSITION_PRICE_CURRENT);
            double sl = PositionGetDouble(POSITION_SL);
            double tp = PositionGetDouble(POSITION_TP);
            
            // Break-even
            if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
            {{
                if(current >= price + InpBreakEvenATR * atr && sl < price)
                    trade.PositionModify(ticket, price + 0.1, tp);
            }}
            else
            {{
                if(current <= price - InpBreakEvenATR * atr && sl > price)
                    trade.PositionModify(ticket, price - 0.1, tp);
            }}
        }}
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
        FAST_EMA=parse_int(params.get("FastEMA", 34), 34),
        SLOW_EMA=parse_int(params.get("SlowEMA", 200), 200),
        ADX_PERIOD=parse_int(params.get("ADXPeriod", 14), 14),
        ADX_MIN=parse_float(params.get("ADXMin", 15.0), 15.0),
        RSI_PERIOD=parse_int(params.get("RSIPeriod", 14), 14),
        RSI_LONG_MIN=parse_float(params.get("RSILongMin", 50.0), 50.0),
        RSI_SHORT_MAX=parse_float(params.get("RSIShortMax", 50.0), 50.0),
        BBWR_PERIOD=parse_int(params.get("BBWRPeriod", 20), 20),
        SL_ATR=parse_float(params.get("StopLossATR", 3.0), 3.0),
        TP_ATR=parse_float(params.get("ProfitTargetATR", 6.5), 6.5),
        TRAIL_ATR=parse_float(params.get("TrailATR", 1.5), 1.5),
        BE_ATR=parse_float(params.get("BreakEvenATR", 1.2), 1.2),
        ATR_PERIOD=parse_int(params.get("ATRPeriod", 14), 14),
        SESSION_FROM=session_from,
        SESSION_TO=session_to,
    )
