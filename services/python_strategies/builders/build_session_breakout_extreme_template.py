from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="session_breakout_extreme",
    description="Session-based breakout for Commodities and Indices",
    family="breakout",
    regime="Trend following",
    sort_order=130
)
def build_session_breakout_extreme_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")

    params = dict(payload.get("params", {}))
    params.setdefault("SessionHighLowPeriod", 20)
    params.setdefault("EntryBufferATR", 0.1)
    params.setdefault("StopLossATR", 2.0)
    params.setdefault("ProfitTargetATR", 4.0)
    params.setdefault("ATRPeriod", 14)
    params.setdefault("ADXPeriod", 14)
    params.setdefault("ADXFilterLevel", 25)
    params.setdefault("ExpiryBars", 5)
    params.setdefault("TrendSMA", 50)
    params.setdefault("mmLots", 0.1)  # Default to 0.1 for safer discovery
    params.setdefault("BreakoutStart", "08:00")
    params.setdefault("BreakoutEnd", "16:00")
    params.setdefault("ExitTime", "21:00")
    params.setdefault("SessionStart", "00:00")
    params.setdefault("SessionEnd", "07:00")
    params.setdefault("TrailingStopATR", 1.5)
    params.setdefault("TrailingActivationATR", 0.0)

    session_start_h = int(str(params["SessionStart"])[:2])
    session_start_m = int(str(params["SessionStart"])[3:])
    session_end_h = int(str(params["SessionEnd"])[:2])
    session_end_m = int(str(params["SessionEnd"])[3:])

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(params.get("TrendSMA", 50)) + 30,
        indicators=[
            IndicatorSpec("session_high", "sq_session_ohlc", {"df": "df", "type_": 2, "start_hours": session_start_h, "start_minutes": session_start_m, "end_hours": session_end_h, "end_minutes": session_end_m}),
            IndicatorSpec("session_low", "sq_session_ohlc", {"df": "df", "type_": 3, "start_hours": session_start_h, "start_minutes": session_start_m, "end_hours": session_end_h, "end_minutes": session_end_m}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ATRPeriod")}),
            IndicatorSpec("adx_data", "sq_adx", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ADXPeriod")}, outputs={"adx": "adx"}),
            IndicatorSpec("trend_sma", "sma", {"close": "close", "period": _param_payload(params, "TrendSMA")}),
        ],
        series=[],
        exits=[
            ExitRuleSpec(
                name="eod_exit",
                when='_hhmm(ctx.time) >= (int(str(self.p("ExitTime"))[:2]) * 100 + int(str(self.p("ExitTime"))[3:]))'
            )
        ],
        entries=[
            EntryRuleSpec(
                name="buy_breakout",
                side="long",
                order_type="buy_stop",
                price='float(df["session_high"].iloc[i-1]) + float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])',
                when='_hhmm(ctx.time) == (int(str(self.p("BreakoutStart"))[:2]) * 100 + int(str(self.p("BreakoutStart"))[3:])) and float(df["adx"].iloc[i-1]) >= float(self.p("ADXFilterLevel")) and (float(self.p("TrendSMA")) <= 0 or float(df["close"].iloc[i-1]) > float(df["trend_sma"].iloc[i-1]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["session_high"].iloc[i-1]) + float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])) - float(self.p("StopLossATR")) * float(df["atr"].iloc[i-1])',
                take_profit='(float(df["session_high"].iloc[i-1]) + float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])) + float(self.p("ProfitTargetATR")) * float(df["atr"].iloc[i-1])',
                trail_dist='float(self.p("TrailingStopATR")) * float(df["atr"].iloc[i-1])',
                trail_activation='float(self.p("TrailingActivationATR")) * float(df["atr"].iloc[i-1])',
                expiry_bars=int(params.get("ExpiryBars", 5))
            ),
            EntryRuleSpec(
                name="sell_breakout",
                side="short",
                order_type="sell_stop",
                price='float(df["session_low"].iloc[i-1]) - float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])',
                when='_hhmm(ctx.time) == (int(str(self.p("BreakoutStart"))[:2]) * 100 + int(str(self.p("BreakoutStart"))[3:])) and float(df["adx"].iloc[i-1]) >= float(self.p("ADXFilterLevel")) and (float(self.p("TrendSMA")) <= 0 or float(df["close"].iloc[i-1]) < float(df["trend_sma"].iloc[i-1]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["session_low"].iloc[i-1]) - float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])) + float(self.p("StopLossATR")) * float(df["atr"].iloc[i-1])',
                take_profit='(float(df["session_low"].iloc[i-1]) - float(self.p("EntryBufferATR")) * float(df["atr"].iloc[i-1])) - float(self.p("ProfitTargetATR")) * float(df["atr"].iloc[i-1])',
                trail_dist='float(self.p("TrailingStopATR")) * float(df["atr"].iloc[i-1])',
                trail_activation='float(self.p("TrailingActivationATR")) * float(df["atr"].iloc[i-1])',
                expiry_bars=int(params.get("ExpiryBars", 5))
            )
        ]
    )
