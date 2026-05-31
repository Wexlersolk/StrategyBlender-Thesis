from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_usdjpy_dual_ema_rsi",
    description="USDJPY dual EMA plus RSI breakout family mined from SQX batch.",
    family="fx_breakout",
    regime="FX trend-momentum breakout",
    supported_symbols=("USDJPY", "GBPJPY"),
    supported_timeframes=("M30", "H1", "H4"),
    preferred_timeframes=("M30", "H1", "H4"),
    sort_order=42
)
def build_usdjpy_dual_ema_rsi_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "FastEMA": 21,
        "SlowEMA": 55,
        "RSIPeriod": 14,
        "RSIThreshold": 55,
        "StopLossATR": 1.8,
        "ProfitTargetATR": 3.6,
        "ATRPeriod": 14,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        indicators=[
            IndicatorSpec("ema_f", "ema", {"series": "close", "period": {"param": "FastEMA"}}),
            IndicatorSpec("ema_s", "ema", {"series": "close", "period": {"param": "SlowEMA"}}),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSIPeriod"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
        ],
        series=[
            SeriesSpec("long_entry", '_cross_above(df["ema_f"], df["ema_s"]) & (df["rsi"] > float(self.p("RSIThreshold")))'),
            SeriesSpec("short_entry", '_cross_below(df["ema_f"], df["ema_s"]) & (df["rsi"] < (100.0 - float(self.p("RSIThreshold"))))'),
        ],
        entries=[
            EntryRuleSpec(
                name="long",
                side="long",
                order_type="market",
                when='bool(df["long_entry"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='df["close"].iloc[i-1] - float(self.p("StopLossATR")) * df["atr"].iloc[i-1]',
                take_profit='df["close"].iloc[i-1] + float(self.p("ProfitTargetATR")) * df["atr"].iloc[i-1]',
            ),
            EntryRuleSpec(
                name="short",
                side="short",
                order_type="market",
                when='bool(df["short_entry"].iloc[i-1]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='df["close"].iloc[i-1] + float(self.p("StopLossATR")) * df["atr"].iloc[i-1]',
                take_profit='df["close"].iloc[i-1] - float(self.p("ProfitTargetATR")) * df["atr"].iloc[i-1]',
            ),
        ],
    )
