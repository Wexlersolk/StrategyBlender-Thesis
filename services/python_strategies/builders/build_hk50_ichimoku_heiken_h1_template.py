from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_ichi_heiken_h1",
    description="HK50 H1 Ichimoku plus Heiken reclaim family.",
    family="index_ichi_reclaim",
    regime="Index Ichimoku reclaim with Heiken confirmation",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=71
)
def build_hk50_ichimoku_heiken_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "IchimokuTenkanPrd1": 9,
        "IchimokuKijunPeriod1": 26,
        "IchimokuSenkouPrd1": 52,
        "IndicatorMAPeriod1": 72,
        "Highest_period": 50,
        "Lowest_period": 60,
        "ATRFastPeriod": 14,
        "ATRSlowPeriod": 19,
        "EntryBufferATR": 0.12,
        "StopLossCoef1": 1.6,
        "ProfitTargetCoef1": 4.8,
        "StopLossCoef2": 2.6,
        "ProfitTargetCoef2": 2.4,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:35",
        "FridayExitTime": "22:38",
        "mmLots": 45.0,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 60)),
        lot_value=float(payload.get("lot_value", 0.1285)),
        description=payload.get("description", "HK50 H1 Ichimoku plus Heiken reclaim family mined from Batch1 Strategy 3.12.69."),
        indicators=[
            IndicatorSpec(
                "ichi",
                "sq_ichimoku",
                {
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "tenkan": {"param": "IchimokuTenkanPrd1"},
                    "kijun": {"param": "IchimokuKijunPeriod1"},
                    "senkou": {"param": "IchimokuSenkouPrd1"},
                },
                outputs={"kijun": "ichi_kijun"},
            ),
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "close": "ha_close"}),
            IndicatorSpec("ema_bias", "ema", {"series": "close", "period": {"param": "IndicatorMAPeriod1"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": 0}),
            IndicatorSpec("atr_fast", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRFastPeriod"}}),
            IndicatorSpec("atr_slow", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRSlowPeriod"}}),
        ],
        series=[
            SeriesSpec("long_signal", '(df["close"].shift(1) > df["ichi_kijun"].shift(1)) & (df["ha_close"].shift(1) > df["ha_open"].shift(1)) & (df["close"].shift(1) > df["ema_bias"].shift(1))'),
            SeriesSpec("short_signal", '(df["close"].shift(1) < df["ichi_kijun"].shift(1)) & (df["ha_close"].shift(1) < df["ha_open"].shift(1)) & (df["close"].shift(1) < df["ema_bias"].shift(1))'),
            SeriesSpec("long_exit_signal", 'df["ha_close"].shift(1) < df["ha_open"].shift(1)'),
            SeriesSpec("short_exit_signal", 'df["ha_close"].shift(1) > df["ha_open"].shift(1)'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
            ExitRuleSpec("long_exit", 'ctx.has_long and bool(df["long_exit_signal"].eq(True).iloc[i])'),
            ExitRuleSpec("short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_ichi_heiken_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and not bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest"].iloc[i]) + (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["highest"].iloc[i]) + (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))) - (float(self.p("StopLossCoef1")) * float(df["atr_fast"].iloc[i]))',
                take_profit='(float(df["highest"].iloc[i]) + (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_slow"].iloc[i]))',
                expiry_bars=2,
                comment="hk50_ichi_heiken_long",
            ),
            EntryRuleSpec(
                name="hk50_ichi_heiken_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest"].iloc[i]) - (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["lowest"].iloc[i]) - (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))) + (float(self.p("StopLossCoef2")) * float(df["atr_fast"].iloc[i]))',
                take_profit='(float(df["lowest"].iloc[i]) - (float(self.p("EntryBufferATR")) * float(df["atr_fast"].iloc[i]))) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_slow"].iloc[i]))',
                expiry_bars=2,
                comment="hk50_ichi_heiken_short",
            ),
        ],
    )
