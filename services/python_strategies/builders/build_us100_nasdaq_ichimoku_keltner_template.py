from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_us100_nasdaq_ichi_keltner",
    description="US100 H1 Ichimoku and Keltner breakout family.",
    family="index_breakout",
    regime="Index Ichimoku breakout",
    supported_symbols=("US100.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=62
)
def build_us100_nasdaq_ichimoku_keltner_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "SMMAPeriod1": 40,
        "IchimokuTenkanPrd1": 9,
        "IchimokuKijunPeriod1": 26,
        "IchimokuSenkouPrd1": 16,
        "KeltnerChannelPrd1": 70,
        "KeltnerMult1": 2.25,
        "LowestPeriod1": 25,
        "ATRPeriod1": 14,
        "ATRPeriod2": 20,
        "ATRPeriod3": 19,
        "ATRPeriod4": 50,
        "PriceEntryMult1": 1.6,
        "PriceEntryMult2": 1.2,
        "ProfitTargetCoef1": 5.0,
        "StopLossCoef1": 1.9,
        "ProfitTargetCoef2": 3.6,
        "StopLossCoef2": 1.5,
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
        min_bars=int(payload.get("min_bars", 70)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "US100 Ichimoku/Keltner pullback family derived from NASDAQ Strategy 4.15.65."),
        indicators=[
            IndicatorSpec("smma_close", "smma", {"series": "close", "period": {"param": "SMMAPeriod1"}}),
            IndicatorSpec("ichi", "sq_ichimoku", {"high": "high", "low": "low", "close": "close", "tenkan": {"param": "IchimokuTenkanPrd1"}, "kijun": {"param": "IchimokuKijunPeriod1"}, "senkou": {"param": "IchimokuSenkouPrd1"}}, outputs={"kijun": "ichi_kijun"}),
            IndicatorSpec("kc", "sq_keltner_channel", {"high": "high", "low": "low", "close": "close", "period": {"param": "KeltnerChannelPrd1"}, "multiplier": {"param": "KeltnerMult1"}}, outputs={"middle": "kc_mid", "upper": "kc_upper", "lower": "kc_lower"}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod1"}, "mode": 3}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
            IndicatorSpec("atr_3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod3"}}),
            IndicatorSpec("atr_4", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod4"}}),
        ],
        series=[
            SeriesSpec("long_signal", '(df["low"] <= df["smma_close"]) & (df["close"] > df["ichi_kijun"])'),
            SeriesSpec("short_signal", '(df["high"] >= df["smma_close"]) & (df["close"] < df["ichi_kijun"])'),
            SeriesSpec("long_exit_signal", 'df["ichi_kijun"] < df["kc_mid"]'),
            SeriesSpec("short_exit_signal", 'df["close"] > df["smma_close"]'),
        ],
        exits=[
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
            ExitRuleSpec("long_exit", 'ctx.has_long and bool(df["long_exit_signal"].eq(True).iloc[i])'),
            ExitRuleSpec("short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="us100_ichi_keltner_long",
                side="long",
                order_type="buy_limit",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest_level"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["lowest_level"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) - (float(self.p("StopLossCoef1")) * float(df["atr_1"].iloc[i]))',
                take_profit='(float(df["lowest_level"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_3"].iloc[i]))',
                expiry_bars=18,
                comment="us100_ichi_keltner_long",
            ),
            EntryRuleSpec(
                name="us100_ichi_keltner_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["ichi_kijun"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_4"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["ichi_kijun"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_4"].iloc[i]))) + (float(self.p("StopLossCoef2")) * float(df["atr_3"].iloc[i]))',
                take_profit='(float(df["ichi_kijun"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_4"].iloc[i]))) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_1"].iloc[i]))',
                expiry_bars=3,
                comment="us100_ichi_keltner_short",
            ),
        ],
    )
