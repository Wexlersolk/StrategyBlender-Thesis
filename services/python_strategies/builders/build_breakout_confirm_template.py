from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="breakout_confirm",
    description="Breakout confirmation with momentum",
    family="breakout",
    regime="Breakout confirmation",
    sort_order=110
)
def build_breakout_confirm_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    direction = payload.get("direction", "long")
    if direction not in {"long", "short"}:
        raise ValueError("breakout_confirm.direction must be 'long' or 'short'")

    highest_period = str(payload.get("highest_period_param", "HighestPeriod"))
    lowest_period = str(payload.get("lowest_period_param", "LowestPeriod"))
    atr_period = str(payload.get("atr_period_param", "ATRPeriod"))
    lots = str(payload.get("lots_param", "mmLots"))
    stop_loss = str(payload.get("stop_loss_atr_param", "StopLossATR"))
    take_profit = str(payload.get("take_profit_atr_param", "ProfitTargetATR"))
    max_distance = str(payload.get("max_distance_pct_param", "MaxDistancePct"))
    bbwr_period = str(payload.get("bbwr_period_param", "BBWRPeriod"))
    bbwr_min = str(payload.get("bbwr_min_param", "BBWRMin"))
    ema_period = str(payload.get("ema_period_param", "EMAPeriod"))
    time_from = str(payload.get("time_from_param", "SignalTimeRangeFrom"))
    time_to = str(payload.get("time_to_param", "SignalTimeRangeTo"))
    trail_dist = str(payload.get("trail_dist_param", "TrailingStopATR"))

    params = dict(payload.get("params", {}))
    params.setdefault(highest_period, 20)
    params.setdefault(lowest_period, 20)
    params.setdefault(atr_period, 14)
    params.setdefault(lots, 1.0)
    params.setdefault(stop_loss, 2.0)
    params.setdefault(take_profit, 3.0)
    params.setdefault(max_distance, 3.0)
    params.setdefault(bbwr_period, 20)
    params.setdefault(bbwr_min, 0.0)
    params.setdefault(ema_period, 200)
    params.setdefault(time_from, "00:00")
    params.setdefault(time_to, "23:59")
    params.setdefault(trail_dist, 0.0)

    long_side = direction == "long"
    level_col = "highest_level" if long_side else "lowest_level"
    
    # We use iloc[i] here because _patch_iloc will change it to iloc[i-1] 
    # which correctly looks at the COMPLETED bar that just closed.
    price_expr = f'float(df["{level_col}"].iloc[i])'
    distance_check = f'abs({price_expr} - ctx.open) / max(abs(ctx.open), 1e-9) * 100.0 <= float(self.p("{max_distance}"))'
    
    # Trend filter: Long above EMA, Short below EMA
    trend_filter = f'ctx.open > float(df["ema"].iloc[i])' if long_side else f'ctx.open < float(df["ema"].iloc[i])'
    
    # Time filter
    time_filter = f'_in_time_window(ctx.time, str(self.p("{time_from}")), str(self.p("{time_to}")))'

    # Signal: current bar broke the level of the previous bar.
    # Note: no shift(1) here because _patch_iloc will handle it.
    signal_expr = (
        f'(df["close"] > df["{level_col}"].shift(1)) & (df["bbwr"] >= float(self.p("{bbwr_min}")))'
        if long_side
        else f'(df["close"] < df["{level_col}"].shift(1)) & (df["bbwr"] >= float(self.p("{bbwr_min}")))'
    )
    stop_loss_expr = (
        f'{price_expr} - float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))'
        if long_side
        else f'{price_expr} + float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))'
    )
    take_profit_expr = (
        f'{price_expr} + float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))'
        if long_side
        else f'{price_expr} - float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))'
    )
    trail_dist_expr = f'float(df["atr"].iloc[i]) * float(self.p("{trail_dist}"))'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 25)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "Breakout confirmation template with momentum, time filter, and trailing stop."),
        indicators=[
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": _param_payload(params, highest_period), "mode": 2}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": _param_payload(params, lowest_period), "mode": 3}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, atr_period)}),
            IndicatorSpec("bbwr", "sq_bb_width_ratio", {"series": "close", "period": _param_payload(params, bbwr_period), "deviations": 2.0}),
            IndicatorSpec("ema", "sq_ema", {"series": "close", "period": _param_payload(params, ema_period)}),
        ],
        series=[
            SeriesSpec("entry_signal", signal_expr),
        ],
        entries=[
            EntryRuleSpec(
                name=f"{direction}_breakout",
                side=direction,
                order_type="buy_stop" if long_side else "sell_stop",
                when=f'bool(df["entry_signal"].iloc[i]) and ({distance_check}) and ({trend_filter}) and ({time_filter})',
                price=price_expr,
                lots=f'float(self.p("{lots}"))',
                stop_loss=stop_loss_expr,
                take_profit=take_profit_expr,
                trail_dist=trail_dist_expr,
                comment=f"template_breakout_{direction}",
                expiry_bars=int(payload.get("expiry_bars", 3)),
            )
        ],
    )
