from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="trend_pullback",
    description="Trend following with pullback entry",
    family="trend",
    regime="Trend following",
    sort_order=100
)
def build_trend_pullback_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    direction = payload.get("direction", "long")
    if direction not in {"long", "short"}:
        raise ValueError("trend_pullback.direction must be 'long' or 'short'")

    fast_ema = str(payload.get("fast_ema_param", "FastEMA"))
    slow_ema = str(payload.get("slow_ema_param", "SlowEMA"))
    atr_period = str(payload.get("atr_period_param", "ATRPeriod"))
    lots = str(payload.get("lots_param", "mmLots"))
    stop_loss = str(payload.get("stop_loss_atr_param", "StopLossATR"))
    take_profit = str(payload.get("take_profit_atr_param", "ProfitTargetATR"))
    wt_channel = str(payload.get("wt_channel_param", "WaveTrendChannel"))
    wt_average = str(payload.get("wt_average_param", "WaveTrendAverage"))
    exit_after = str(payload.get("exit_after_bars_param", "ExitAfterBars"))
    h4_filter = str(payload.get("h4_filter_param", "H4TrendFilter"))
    h4_ema = str(payload.get("h4_ema_param", "H4TrendEMA"))

    params = dict(payload.get("params", {}))
    params.setdefault(fast_ema, 20)
    params.setdefault(slow_ema, 50)
    params.setdefault(atr_period, 14)
    params.setdefault(lots, 1.0)
    params.setdefault(stop_loss, 2.0)
    params.setdefault(take_profit, 3.0)
    params.setdefault(wt_channel, 9)
    params.setdefault(wt_average, 21)
    params.setdefault(exit_after, 12)
    params.setdefault(h4_filter, False)
    params.setdefault(h4_ema, 55)

    long_side = direction == "long"
    trend_expr = 'df["ema_fast"] > df["ema_slow"]' if long_side else 'df["ema_fast"] < df["ema_slow"]'
    
    # H4 Trend Filter (Approximation: H4 EMA 55 ~= H1 EMA 220)
    h4_trend_expr = f'(df["close"] > df["h4_ema"])' if long_side else f'(df["close"] < df["h4_ema"])'
    full_trend_expr = f'({trend_expr}) & ((bool(self.p("{h4_filter}")) == False) | {h4_trend_expr})'

    wave_expr = 'df["wt_main"] > df["wt_signal"]' if long_side else 'df["wt_main"] < df["wt_signal"]'
    pullback_expr = 'df["close"] <= df["ema_fast"]' if long_side else 'df["close"] >= df["ema_fast"]'
    stop_loss_expr = (
        f'ctx.open - float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))'
        if long_side
        else f'ctx.open + float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))'
    )
    take_profit_expr = (
        f'ctx.open + float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))'
        if long_side
        else f'ctx.open - float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))'
    )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 220)), # Increased min_bars for H4 EMA
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "Trend-pullback template with optional H4 MTF filter."),
        indicators=[
            IndicatorSpec("ema_fast", "ema", {"series": "close", "period": _param_payload(params, fast_ema)}),
            IndicatorSpec("ema_slow", "ema", {"series": "close", "period": _param_payload(params, slow_ema)}),
            IndicatorSpec("h4_ema", "ema", {"series": "close", "period": _param_payload(params, h4_ema, multiplier=4)}),
            IndicatorSpec(
                "wavetrend",
                "sq_wave_trend",
                {"high": "high", "low": "low", "close": "close", "channel_length": _param_payload(params, wt_channel), "average_length": _param_payload(params, wt_average)},
                outputs={"main": "wt_main", "signal": "wt_signal"},
            ),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, atr_period)}),
        ],
        series=[
            SeriesSpec(
                "entry_signal",
                f'({full_trend_expr}) & ({pullback_expr}) & ({wave_expr})',
            ),
        ],
        entries=[
            EntryRuleSpec(
                name=f"{direction}_entry",
                side=direction,
                order_type="market",
                when='bool(df["entry_signal"].iloc[i])',
                lots=f'float(self.p("{lots}"))',
                stop_loss=stop_loss_expr,
                take_profit=take_profit_expr,
                comment=f"template_{direction}",
                exit_after_bars=f'int(self.p("{exit_after}"))',
            )
        ],
    )
