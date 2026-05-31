from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="us100_ny_momentum",
    description="Captures the NY session momentum on US100.",
    family="index_momentum",
    regime="Intraday Momentum",
    supported_symbols=("US100.cash", "US30.cash", "US500.cash"),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=65
)
def build_us100_ny_momentum_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "EMAPeriod": 200,
        "ATRPeriod": 14,
        "StopLossATR": 2.5,
        "ProfitTargetATR": 6.0,
        "TrailingStopATR": 1.5,
        "NYOpenHour": 13, # UTC
        "NYCloseHour": 20, # UTC
        "mmLots": 1.0,
    }
    for k, v in defaults.items():
        params.setdefault(k, v)

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(params["EMAPeriod"]) + 20,
        indicators=[
            IndicatorSpec("ema_trend", "ema", {"series": "close", "period": _param_payload(params, "EMAPeriod")}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ATRPeriod")}),
        ],
        series=[
            SeriesSpec("pre_market_high", 'df["high"].shift(1)'),
            SeriesSpec("pre_market_low", 'df["low"].shift(1)'),
        ],
        entries=[
            EntryRuleSpec(
                name="ny_momentum_long",
                side="long",
                order_type="buy_stop",
                price='float(df["pre_market_high"].iloc[i])',
                when='int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i-1]) > float(df["ema_trend"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["pre_market_high"].iloc[i]) - float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit='float(df["pre_market_high"].iloc[i]) + float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_long",
                expiry_bars=1,
            ),
            EntryRuleSpec(
                name="ny_momentum_short",
                side="short",
                order_type="sell_stop",
                price='float(df["pre_market_low"].iloc[i])',
                when='int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i-1]) < float(df["ema_trend"].iloc[i-1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["pre_market_low"].iloc[i]) + float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit='float(df["pre_market_low"].iloc[i]) - float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_short",
                expiry_bars=1,
            ),
        ],
        exits=[
            ExitRuleSpec("ny_session_close", f'int(ctx.time.hour) >= int(self.p("NYCloseHour"))'),
        ]
    )
