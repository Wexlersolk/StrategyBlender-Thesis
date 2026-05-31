from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_usdjpy_vwap_wt",
    description="USDJPY VWAP plus WaveTrend breakout family mined from SQX batch.",
    family="fx_breakout_continuation",
    regime="FX VWAP breakout",
    supported_symbols=("USDJPY", "AUDUSD", "GBPJPY"),
    supported_timeframes=("M30", "H1", "H4"),
    preferred_timeframes=("M30", "H1", "H4"),
    sort_order=40
)
def build_usdjpy_sqx_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "EMAPeriod1": 20,
        "VWAPPeriod1": 77,
        "WaveTrendChannel": 9,
        "WaveTrendAverage": 60,
        "IndicatorCrsMAPrd1": 35,
        "IndicatorCrsMAPrd2": 31,
        "PriceEntryMult1": 0.3,
        "ExitAfterBars1": 14,
        "ProfitTargetCoef1": 3.0,
        "StopLossCoef1": 2.8,
        "ATRPeriod1": 19,
        "ATRPeriod2": 14,
        "HighestPeriod": 20,
        "mmLots": 1.0,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 12)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "USDJPY SQX EMA/VWAP/WaveTrend breakout family."),
        indicators=[
            IndicatorSpec("ema_1", "ema", {"series": "close", "period": {"param": "EMAPeriod1"}}),
            IndicatorSpec("wt", "sq_wave_trend", {"high": "high", "low": "low", "close": "close", "channel_length": {"param": "WaveTrendChannel"}, "average_length": {"param": "WaveTrendAverage"}}, outputs={"main": "wavetrend"}),
            IndicatorSpec("vwap", "sq_vwap", {"open_": "open", "high": "high", "low": "low", "close": "close", "volume": "volume", "period": {"param": "VWAPPeriod1"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 3}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
        ],
        series=[
            SeriesSpec("long_entry_signal", '_count_compare(df["open"], df["ema_1"].shift(2), 5, 3, greater=False, allow_equal=False)'),
            SeriesSpec("long_exit_signal", '_cross_below(df["vwap"].shift(3), sma(df["vwap"].shift(3), int(self.p("IndicatorCrsMAPrd1")))) & (df["wavetrend"].shift(1) > 0)'),
        ],
        exits=[
            ExitRuleSpec("long_exit", 'ctx.has_long and bool(df["long_exit_signal"].iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="usdjpy_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_entry_signal"].iloc[i])',
                price='float(df["highest"].iloc[i - 2]) + float(self.p("PriceEntryMult1")) * float(df["atr"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='(float(df["highest"].iloc[i - 2]) + float(self.p("PriceEntryMult1")) * float(df["atr"].iloc[i - 1])) - float(self.p("StopLossCoef1")) * float(df["atr_2"].iloc[i - 1])',
                take_profit='(float(df["highest"].iloc[i - 2]) + float(self.p("PriceEntryMult1")) * float(df["atr"].iloc[i - 1])) + float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i - 1])',
                exit_after_bars='int(self.p("ExitAfterBars1"))',
                comment="sqx_usdjpy_long",
                expiry_bars=17,
            ),
        ],
    )
