from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_us100_nasdaq_smma_keltner",
    description="US100 H1 SMMA and Keltner breakout family.",
    family="index_breakout",
    regime="Index volatility breakout",
    supported_symbols=("US100.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=60
)
def build_us100_nasdaq_smma_keltner_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "SMMAPeriod1": 12,
        "EWMAPeriod1": 20,
        "ROCPeriod1": 12,
        "ROCThreshold1": 50.3,
        "KCFastPeriod1": 20,
        "KCFastMult1": 2.5,
        "KCSlowPeriod1": 73,
        "KCSlowMult1": 2.4,
        "ATRPeriod1": 50,
        "ATRPeriod2": 19,
        "ATRPeriod3": 14,
        "ATRPeriod4": 65,
        "PriceEntryMult1": 2.0,
        "ExitAfterBars1": 12,
        "ProfitTargetCoef1": 6.0,
        "StopLossCoef1": 2.2,
        "ProfitTargetCoef2": 5.6,
        "StopLossCoef2": 2.3,
        "TrailingStop1": 360.0,
        "TrailingActCef1": 3.9,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
        "FridayExitTime": "22:38",
        "mmLots": 1.0,
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
        description=payload.get("description", "US100 SMMA/Keltner asymmetry family derived from NASDAQ Strategy 2.13.62."),
        indicators=[
            IndicatorSpec("smma_low", "smma", {"series": "low", "period": {"param": "SMMAPeriod1"}}),
            IndicatorSpec("smma_high", "smma", {"series": "high", "period": {"param": "SMMAPeriod1"}}),
            IndicatorSpec("ema_close", "ema", {"series": "close", "period": {"param": "EWMAPeriod1"}}),
            IndicatorSpec("kc_fast", "sq_keltner_channel", {"high": "high", "low": "low", "close": "close", "period": {"param": "KCFastPeriod1"}, "multiplier": {"param": "KCFastMult1"}}, outputs={"middle": "kc_fast_mid", "upper": "kc_fast_upper", "lower": "kc_fast_lower"}),
            IndicatorSpec("kc_slow", "sq_keltner_channel", {"high": "high", "low": "low", "close": "close", "period": {"param": "KCSlowPeriod1"}, "multiplier": {"param": "KCSlowMult1"}}, outputs={"middle": "kc_slow_mid", "upper": "kc_slow_upper", "lower": "kc_slow_lower"}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
            IndicatorSpec("atr_3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod3"}}),
            IndicatorSpec("atr_4", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod4"}}),
        ],
        series=[
            SeriesSpec("roc", '((df["close"] / df["close"].shift(int(self.p("ROCPeriod1")))) - 1.0) * 100.0 + 50.0'),
            SeriesSpec("long_signal", 'df["smma_low"] > df["ema_close"]'),
            SeriesSpec("short_signal", 'df["smma_high"] < df["ema_close"]'),
            SeriesSpec("short_exit_signal", '_falling(df["close"], 2, 1) & (df["roc"] > float(self.p("ROCThreshold1")))'),
        ],
        exits=[
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
            ExitRuleSpec("short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="us100_smma_keltner_long",
                side="long",
                order_type="buy_limit",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["kc_fast_lower"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["kc_fast_lower"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) - (float(self.p("StopLossCoef1")) * float(df["atr_3"].iloc[i]))',
                take_profit='(float(df["kc_fast_lower"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i]))',
                exit_after_bars='int(self.p("ExitAfterBars1"))',
                expiry_bars=4,
                comment="us100_smma_keltner_long",
            ),
            EntryRuleSpec(
                name="us100_smma_keltner_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["kc_slow_lower"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["kc_slow_lower"].iloc[i]) + (float(self.p("StopLossCoef2")) * float(df["atr_3"].iloc[i]))',
                take_profit='float(df["kc_slow_lower"].iloc[i]) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_2"].iloc[i]))',
                trail_dist='float(self.p("TrailingStop1"))',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr_4"].iloc[i])',
                expiry_bars=4,
                comment="us100_smma_keltner_short",
            ),
        ],
    )
