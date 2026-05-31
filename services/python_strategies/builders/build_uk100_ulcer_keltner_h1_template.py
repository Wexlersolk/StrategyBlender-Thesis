from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_uk100_ulcer_keltner_h1",
    description="UK100 H1 Ulcer Index and Keltner breakout family.",
    family="index_volatility",
    regime="Index volatility mean-reversion",
    supported_symbols=("UK100.cash", "GER40.cash"),
    supported_timeframes=("M30", "H1"),
    preferred_timeframes=("M30", "H1"),
    sort_order=63
)
def build_uk100_ulcer_keltner_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "UlcerPeriod": 48,
        "KCPeriod": 20,
        "KCMult1": 2.25,
        "KCMult2": 2.5,
        "ATR1_period": 50,
        "ATR2_period": 19,
        "ATR3_period": 100,
        "ATR4_period": 14,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:26",
        "EntryOffsetCoef1": 2.30,
        "StopLossCoef1": 1.5,
        "ProfitTargetCoef1": 3.5,
        "StopLossCoef2": 2.0,
        "ProfitTargetCoef2": 3.4,
        "TrailingActCoef1": 1.2,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 60)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "UK100 H1 Ulcer/Keltner/Heiken Ashi family."),
        indicators=[
            IndicatorSpec("ulcer", "sq_ulcer_index", {"close": "close", "period": {"param": "UlcerPeriod"}}),
            IndicatorSpec("kc_1", "sq_keltner_channel", {"high": "high", "low": "low", "close": "close", "period": {"param": "KCPeriod"}, "multiplier": {"param": "KCMult1"}}, outputs={"upper": "kc1_upper", "lower": "kc1_lower"}),
            IndicatorSpec("kc_2", "sq_keltner_channel", {"high": "high", "low": "low", "close": "close", "period": {"param": "KCPeriod"}, "multiplier": {"param": "KCMult2"}}, outputs={"upper": "kc2_upper", "lower": "kc2_lower"}),
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "close": "ha_close"}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR1_period"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR2_period"}}),
            IndicatorSpec("atr_3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR3_period"}}),
            IndicatorSpec("atr_4", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR4_period"}}),
        ],
        series=[
            SeriesSpec("long_signal", '_rising(df["ulcer"], 2, 1) & (df["close"] < df["kc1_lower"])'),
            SeriesSpec("short_signal", '_rising(df["ulcer"], 2, 1) & (df["close"] > df["kc1_upper"])'),
            SeriesSpec("short_exit_signal", 'df["kc2_lower"].shift(2) < df["kc2_lower"].rolling(558, min_periods=50).quantile(0.532)'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
            ExitRuleSpec("uk100_short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="uk100_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i])',
                price='max(float(ctx.df["high"].iloc[i - 3]), float(df["ha_open"].iloc[i - 3]), float(df["ha_close"].iloc[i - 3])) - (float(self.p("EntryOffsetCoef1")) * float(df["atr_1"].iloc[i - 3]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(max(float(ctx.df["high"].iloc[i - 3]), float(df["ha_open"].iloc[i - 3]), float(df["ha_close"].iloc[i - 3])) - (float(self.p("EntryOffsetCoef1")) * float(df["atr_1"].iloc[i - 3]))) - (float(self.p("StopLossCoef1")) * float(df["atr_2"].iloc[i - 1]))',
                take_profit='(max(float(ctx.df["high"].iloc[i - 3]), float(df["ha_open"].iloc[i - 3]), float(df["ha_close"].iloc[i - 3])) - (float(self.p("EntryOffsetCoef1")) * float(df["atr_1"].iloc[i - 3]))) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i - 1]))',
                comment="uk100_long",
                expiry_bars=6,
            ),
            EntryRuleSpec(
                name="uk100_short",
                side="short",
                order_type="market",
                when='bool(df["short_signal"].eq(True).iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open + (float(self.p("StopLossCoef2")) * float(df["atr_4"].iloc[i - 1]))',
                take_profit='ctx.open - (float(self.p("ProfitTargetCoef2")) * float(df["atr_4"].iloc[i - 1]))',
                trail_activation='float(self.p("TrailingActCoef1")) * float(df["atr_3"].iloc[i - 1])',
                comment="uk100_short",
            ),
        ],
    )
