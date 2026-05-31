from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_fx_h4_swing_reversion",
    description="Generic H4 swing-reversion family using ATR and BB.",
    family="market_reversion",
    regime="Market swing reversal",
    supported_symbols=(),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=52
)
def build_fx_h4_swing_reversion_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "BBPeriod": 20,
        "BBMult": 2.0,
        "WPRPeriod": 14,
        "WPROversold": -80.0,
        "WPROverbought": -20.0,
        "StopLossATR": 2.0,
        "ProfitTargetATR": 3.0,
        "ATRPeriod": 14,
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
            IndicatorSpec(
                "bb",
                "bollinger_bands",
                {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "BBPeriod"}, "deviations": {"param": "BBMult"}},
                outputs={"upper": "bb_up", "lower": "bb_low"},
            ),
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPRPeriod"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
        ],
        series=[
            SeriesSpec("long_entry", '(df["low"] < df["bb_low"]) & (df["wpr"] < float(self.p("WPROversold")))'),
            SeriesSpec("short_entry", '(df["high"] > df["bb_up"]) & (df["wpr"] > float(self.p("WPROverbought")))'),
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
