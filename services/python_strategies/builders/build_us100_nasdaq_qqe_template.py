from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_us100_nasdaq_qqe",
    description="US100 H1 QQE breakout family.",
    family="index_momentum",
    regime="Index QQE momentum",
    supported_symbols=("US100.cash", "AUDUSD", "GER40.cash"),
    supported_timeframes=("H1", "H4"),
    preferred_timeframes=("H1",),
    sort_order=61
)
def build_us100_nasdaq_qqe_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "QQERsiPeriod1": 14,
        "QQESmooth1": 5,
        "QQERsiPeriod2": 69,
        "QQESmooth2": 5,
        "SMAEntryPeriod1": 53,
        "SessionLowLookback": 14,
        "ATRPeriod1": 40,
        "ATRPeriod2": 19,
        "ATRPeriod3": 14,
        "ATRPeriod4": 10,
        "PriceEntryMult1": 1.2,
        "PriceEntryMult2": 0.9,
        "ExitAfterBars1": 18,
        "ExitAfterBars2": 19,
        "ProfitTargetCoef1": 4.2,
        "StopLossCoef1": 1.9,
        "ProfitTargetCoef2": 3.7,
        "StopLossCoef2": 1.7,
        "TrailingStopCoef1": 1.0,
        "TrailingStop1": 105.0,
        "TrailingActivation1": 45.0,
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
        min_bars=int(payload.get("min_bars", 80)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "US100 QQE-style breakout family derived from NASDAQ Strategy 3.14.66."),
        indicators=[
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "close": "ha_close"}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
            IndicatorSpec("atr_3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod3"}}),
            IndicatorSpec("atr_4", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod4"}}),
        ],
        series=[
            SeriesSpec("median_price", '(df["high"] + df["low"]) / 2.0'),
            SeriesSpec("sma_entry", 'sma(df["median_price"], int(self.p("SMAEntryPeriod1")))'),
            SeriesSpec("ha_floor", 'df[["low", "ha_open", "ha_close"]].min(axis=1)'),
            SeriesSpec("rsi_1", '100.0 - (100.0 / (1.0 + (df["close"].diff().clip(lower=0).rolling(int(self.p("QQERsiPeriod1")), min_periods=1).mean() / df["close"].diff().clip(upper=0).abs().rolling(int(self.p("QQERsiPeriod1")), min_periods=1).mean().replace(0.0, np.nan)))).fillna(50.0)'),
            SeriesSpec("qqe_main_1", 'sma(df["rsi_1"], int(self.p("QQESmooth1")))'),
            SeriesSpec("qqe_sig_1", 'sma(df["qqe_main_1"], int(self.p("QQESmooth1")) + 1)'),
            SeriesSpec("rsi_2", '100.0 - (100.0 / (1.0 + (df["close"].diff().clip(lower=0).rolling(int(self.p("QQERsiPeriod2")), min_periods=1).mean() / df["close"].diff().clip(upper=0).abs().rolling(int(self.p("QQERsiPeriod2")), min_periods=1).mean().replace(0.0, np.nan)))).fillna(50.0)'),
            SeriesSpec("qqe_main_2", 'sma(df["rsi_2"], int(self.p("QQESmooth2")))'),
            SeriesSpec("qqe_sig_2", 'sma(df["qqe_main_2"], int(self.p("QQESmooth2")) + 1)'),
            SeriesSpec("session_floor", 'df["low"].rolling(int(self.p("SessionLowLookback")), min_periods=2).min()'),
            SeriesSpec("long_signal", 'df["qqe_main_1"] > df["qqe_sig_1"]'),
            SeriesSpec("short_signal", 'df["qqe_main_1"] < df["qqe_sig_1"]'),
            SeriesSpec("long_exit_signal", 'df["close"] <= df["session_floor"]'),
            SeriesSpec("short_exit_signal", 'df["qqe_main_2"] > df["qqe_sig_2"]'),
        ],
        exits=[
            ExitRuleSpec("friday_exit", 'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))'),
            ExitRuleSpec("long_exit", 'ctx.has_long and bool(df["long_exit_signal"].eq(True).iloc[i])'),
            ExitRuleSpec("short_exit", 'ctx.has_short and bool(df["short_exit_signal"].eq(True).iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="us100_qqe_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["ha_floor"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["ha_floor"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) - (float(self.p("StopLossCoef1")) * float(df["atr_3"].iloc[i]))',
                take_profit='(float(df["ha_floor"].iloc[i]) + (float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i]))) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i]))',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr_4"].iloc[i])',
                exit_after_bars='int(self.p("ExitAfterBars1"))',
                expiry_bars=1,
                comment="us100_qqe_long",
            ),
            EntryRuleSpec(
                name="us100_qqe_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["sma_entry"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_3"].iloc[i]))',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["sma_entry"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_3"].iloc[i]))) + (float(self.p("StopLossCoef2")) * float(df["atr_3"].iloc[i]))',
                take_profit='(float(df["sma_entry"].iloc[i]) - (float(self.p("PriceEntryMult2")) * float(df["atr_3"].iloc[i]))) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_3"].iloc[i]))',
                trail_dist='float(self.p("TrailingStop1"))',
                trail_activation='float(self.p("TrailingActivation1"))',
                exit_after_bars='int(self.p("ExitAfterBars2"))',
                expiry_bars=1,
                comment="us100_qqe_short",
            ),
        ],
    )
