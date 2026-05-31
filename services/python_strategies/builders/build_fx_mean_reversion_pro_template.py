from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="fx_mean_reversion_pro",
    description="Advanced FX Mean Reversion with RSI/Bollinger/ATR and Session filter",
    family="mean_reversion",
    regime="Mean reversion",
    sort_order=125
)
def build_fx_mean_reversion_pro_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")

    params = dict(payload.get("params", {}))
    params.setdefault("BBPeriod", 20)
    params.setdefault("BBDev", 2.0)
    params.setdefault("RSIPeriod", 14)
    params.setdefault("RSIOverbought", 70)
    params.setdefault("RSIOversold", 30)
    params.setdefault("ATRPeriod", 14)
    params.setdefault("StopLossATR", 2.0)
    params.setdefault("ProfitTargetATR", 2.0)
    params.setdefault("mmLots", 1.0)
    params.setdefault("SessionStart", "00:00")
    params.setdefault("SessionEnd", "23:59")

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 100)),
        indicators=[
            IndicatorSpec(
                "bollinger",
                "bollinger_bands",
                {
                    "open_": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "period": _param_payload(params, "BBPeriod"),
                    "deviations": _param_payload(params, "BBDev")
                },
                outputs={"upper": "bb_upper", "lower": "bb_lower"}
            ),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": _param_payload(params, "RSIPeriod")}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ATRPeriod")}),
        ],
        series=[
            SeriesSpec("long_condition", f'(df["close"] < df["bb_lower"]) & (df["rsi"] < float(self.p("RSIOversold")))'),
            SeriesSpec("short_condition", f'(df["close"] > df["bb_upper"]) & (df["rsi"] > float(self.p("RSIOverbought")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="buy_reversion",
                side="long",
                order_type="market",
                when='bool(df["long_condition"].iloc[i]) and _in_time_window(ctx.time, self.p("SessionStart"), self.p("SessionEnd"))',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open - float(df["atr"].iloc[i]) * float(self.p("StopLossATR"))',
                take_profit='ctx.open + float(df["atr"].iloc[i]) * float(self.p("ProfitTargetATR"))',
            ),
            EntryRuleSpec(
                name="sell_reversion",
                side="short",
                order_type="market",
                when='bool(df["short_condition"].iloc[i]) and _in_time_window(ctx.time, self.p("SessionStart"), self.p("SessionEnd"))',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open + float(df["atr"].iloc[i]) * float(self.p("StopLossATR"))',
                take_profit='ctx.open - float(df["atr"].iloc[i]) * float(self.p("ProfitTargetATR"))',
            )
        ]
    )
