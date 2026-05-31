from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_batch_h1",
    description="Native HK50 H1 batch family with AO and LWMA asymmetry.",
    family="index_open_drive",
    regime="Index open-drive breakout",
    supported_symbols=("HK50.cash", "GER40.cash", "US30.cash", "US100.cash"),
    supported_timeframes=("M30", "H1", "H4"),
    preferred_timeframes=("M30", "H1", "H4"),
    sort_order=70
)
def build_hk50_batch_h1_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    normalized_symbol = _canonical_symbol(symbol)
    is_hk50 = normalized_symbol == "HK50.cash"
    defaults = {
        "mmLots": 70.0 if is_hk50 else 1.0,
        "StopLossCoef1": 2.5,
        "ProfitTargetCoef1": 2.8,
        "TrailingActCef1": 1.4,
        "TrailingStop1": 127.5,
        "StopLossCoef2": 3.0,
        "ProfitTargetCoef2": 2.2,
        "TrailingStopCoef1": 1.0,
        "LWMAPeriod1": 14,
        "IndicatorCrsMAPrd1": 47,
        "ATR1_period": 19,
        "ATR2_period": 45,
        "ATR3_period": 14,
        "ATR4_period": 100,
        "Highest_period": 50,
        "Lowest_period": 50,
        "SignalTimeRangeFrom": "00:13" if is_hk50 else "00:00",
        "SignalTimeRangeTo": "00:26" if is_hk50 else "23:59",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    long_signal_mode = str(payload.get("long_signal_mode", "ao_cross"))
    short_signal_mode = str(payload.get("short_signal_mode", "lwma_cross"))
    if long_signal_mode == "range_break":
        long_signal = '(df["close"] > df["highest"].shift(1)) & (df["lwma"] > df["lwma_ma"])'
    elif long_signal_mode == "opening_drive":
        long_signal = '(df["ao"] > 0.0) & (df["close"] > df["lwma"]) & _rising(df["close"], 2, 2)'
    else:
        long_signal = '_cross_above(df["ao"], 0.0)'
    if short_signal_mode == "range_break":
        short_signal = '(df["close"] < df["lowest"].shift(1)) & (df["lwma"] < df["lwma_ma"])'
    elif short_signal_mode == "opening_reversal":
        short_signal = '(df["ao"] < 0.0) & (df["close"] < df["lwma"]) & _falling(df["close"], 2, 2)'
    else:
        short_signal = '_cross_below(df["lwma"], df["lwma_ma"])'
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 55)),
        lot_value=float(payload.get("lot_value", 0.1285 if is_hk50 else 1.0)),
        description=payload.get("description", "HK50 H1 Batch family using AO plus LWMA/EMA asymmetry."),
        indicators=[
            IndicatorSpec("lwma", "wma", {"series": "close", "period": {"param": "LWMAPeriod1"}}),
            IndicatorSpec("lwma_ma", "ema", {"series": "lwma", "period": {"param": "IndicatorCrsMAPrd1"}}),
            IndicatorSpec("atr_19", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR1_period"}}),
            IndicatorSpec("atr_45", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR2_period"}}),
            IndicatorSpec("atr_14", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR3_period"}}),
            IndicatorSpec("atr_100", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATR4_period"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Highest_period"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Lowest_period"}, "mode": 0}),
        ],
        series=[
            SeriesSpec("mid", '(df["high"] + df["low"]) / 2.0'),
            SeriesSpec("ao", 'df["mid"].rolling(5).mean() - df["mid"].rolling(34).mean()'),
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_batch_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and not bool(df["short_signal"].eq(True).iloc[i])',
                price='float(df["highest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i - 1]) - float(self.p("StopLossCoef1")) * float(df["atr_19"].iloc[i - 1])',
                take_profit='float(df["highest"].iloc[i - 1]) + float(self.p("ProfitTargetCoef1")) * float(df["atr_19"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStop1"))',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr_45"].iloc[i - 1])',
                expiry_bars=1,
                comment="hk50_batch_long",
            ),
            EntryRuleSpec(
                name="hk50_batch_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i])',
                price='float(df["lowest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i - 1]) + float(self.p("StopLossCoef2")) * float(df["atr_14"].iloc[i - 1])',
                take_profit='float(df["lowest"].iloc[i - 1]) - float(self.p("ProfitTargetCoef2")) * float(df["atr_19"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr_100"].iloc[i - 1])',
                expiry_bars=1,
                comment="hk50_batch_short",
            ),
        ],
    )
