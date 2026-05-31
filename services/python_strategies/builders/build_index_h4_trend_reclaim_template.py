from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_index_h4_trend_reclaim",
    description="Index H4 trend-reclaim family using Ichimoku and EMA.",
    family="index_trend_reclaim",
    regime="Index long-term trend reclaim",
    supported_symbols=("US100.cash", "GER40.cash", "US30.cash", "HK50.cash"),
    supported_timeframes=("H1", "H4"),
    preferred_timeframes=("H1", "H4"),
    sort_order=50
)
def build_index_h4_trend_reclaim_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "FastEMA": 20,
        "SlowEMA": 100,
        "ATRPeriod": 14,
        "PullbackATR": 1.5,
        "StopLossATR": 2.5,
        "ProfitTargetATR": 5.0,
        "mmLots": 1.0,
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
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
        ],
        series=[
            SeriesSpec("long_entry", '(df["close"] > df["ema_f"]) & (df["ema_f"] > df["ema_s"]) & (df["low"] < (df["ema_f"] - float(self.p("PullbackATR")) * df["atr"]))'),
            SeriesSpec("short_entry", '(df["close"] < df["ema_f"]) & (df["ema_f"] < df["ema_s"]) & (df["high"] > (df["ema_f"] + float(self.p("PullbackATR")) * df["atr"]))'),
        ],
        entries=[
            EntryRuleSpec(
                name="long",
                side="long",
                order_type="market",
                when='bool(df["long_entry"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='df["close"].iloc[i] - float(self.p("StopLossATR")) * df["atr"].iloc[i]',
                take_profit='df["close"].iloc[i] + float(self.p("ProfitTargetATR")) * df["atr"].iloc[i]',
            ),
            EntryRuleSpec(
                name="short",
                side="short",
                order_type="market",
                when='bool(df["short_entry"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='df["close"].iloc[i] + float(self.p("StopLossATR")) * df["atr"].iloc[i]',
                take_profit='df["close"].iloc[i] - float(self.p("ProfitTargetATR")) * df["atr"].iloc[i]',
            ),
        ],
    )
