from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_gold_h4_ichi_momentum",
    description="Generic H4 Ichimoku momentum family.",
    family="market_trend",
    regime="Market Ichimoku momentum",
    supported_symbols=(),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=51
)
def build_gold_h4_ichi_momentum_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "IchimokuTenkan": 9,
        "IchimokuKijun": 26,
        "IchimokuSenkou": 52,
        "RSIPeriod": 14,
        "RSIThreshold": 55,
        "StopLossATR": 2.0,
        "ProfitTargetATR": 4.0,
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
                "ichi",
                "sq_ichimoku",
                {
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "tenkan": {"param": "IchimokuTenkan"},
                    "kijun": {"param": "IchimokuKijun"},
                    "senkou": {"param": "IchimokuSenkou"},
                },
                outputs={"senkou_a": "ichi_senkou_a", "senkou_b": "ichi_senkou_b"},
            ),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSIPeriod"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
        ],
        series=[
            SeriesSpec("long_entry", '(df["close"] > df["ichi_senkou_a"]) & (df["close"] > df["ichi_senkou_b"]) & (df["rsi"] > float(self.p("RSIThreshold")))'),
            SeriesSpec("short_entry", '(df["close"] < df["ichi_senkou_a"]) & (df["close"] < df["ichi_senkou_b"]) & (df["rsi"] < (100.0 - float(self.p("RSIThreshold"))))'),
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
