from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="reversion",
    description="Mean reversion from extreme levels",
    family="mean_reversion",
    regime="Mean reversion",
    sort_order=120
)
def build_reversion_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")

    bb_period = str(payload.get("bb_period_param", "BBPeriod"))
    bb_dev = str(payload.get("bb_dev_param", "BBDev"))
    wpr_period = str(payload.get("wpr_period_param", "WPRPeriod"))
    atr_period = str(payload.get("atr_period_param", "ATRPeriod"))
    lots = str(payload.get("lots_param", "mmLots"))
    stop_loss = str(payload.get("stop_loss_atr_param", "StopLossATR"))
    take_profit = str(payload.get("take_profit_atr_param", "ProfitTargetATR"))
    oversold = str(payload.get("oversold_param", "WPROversold"))
    overbought = str(payload.get("overbought_param", "WPROverbought"))

    params = dict(payload.get("params", {}))
    params.setdefault(bb_period, 20)
    params.setdefault(bb_dev, 2.0)
    params.setdefault(wpr_period, 14)
    params.setdefault(atr_period, 14)
    params.setdefault(lots, 1.0)
    params.setdefault(stop_loss, 1.5)
    params.setdefault(take_profit, 2.0)
    params.setdefault(oversold, -80.0)
    params.setdefault(overbought, -20.0)
    
    # Session defaults
    params.setdefault("SignalTimeRangeFrom", "00:00")
    params.setdefault("SignalTimeRangeTo", "23:59")

    entry_gate = '_in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 20)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "Mean-reversion template generated from the SQ-like rule engine."),
        indicators=[
            IndicatorSpec(
                "bollinger",
                "bollinger_bands",
                {"open_": "open", "high": "high", "low": "low", "close": "close", "period": _param_payload(params, bb_period), "deviations": _param_payload(params, bb_dev), "mode": 0},
                outputs={"upper": "bb_upper", "lower": "bb_lower", "middle": "bb_middle"},
            ),
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, wpr_period)}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, atr_period)}),
        ],
        series=[
            SeriesSpec("long_signal", f'(df["close"] < df["bb_lower"]) & (df["wpr"] <= float(self.p("{oversold}")))'),
            SeriesSpec("short_signal", f'(df["close"] > df["bb_upper"]) & (df["wpr"] >= float(self.p("{overbought}")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="long_reversion",
                side="long",
                order_type="market",
                when=f'{entry_gate} and bool(df["long_signal"].iloc[i])',
                lots=f'float(self.p("{lots}"))',
                stop_loss=f'ctx.open - float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))',
                take_profit=f'ctx.open + float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))',
                comment="template_reversion_long",
            ),
            EntryRuleSpec(
                name="short_reversion",
                side="short",
                order_type="market",
                when=f'{entry_gate} and bool(df["short_signal"].iloc[i])',
                lots=f'float(self.p("{lots}"))',
                stop_loss=f'ctx.open + float(df["atr"].iloc[i]) * float(self.p("{stop_loss}"))',
                take_profit=f'ctx.open - float(df["atr"].iloc[i]) * float(self.p("{take_profit}"))',
                comment="template_reversion_short",
            ),
        ],
    )
