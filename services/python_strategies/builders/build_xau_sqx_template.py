from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_xau_osma_bb",
    description="XAU mean-reversion using OSMA and Bollinger Bands.",
    family="commodity_reversion",
    regime="Commodity mean-reversion",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=30
)
def build_xau_sqx_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "StochK": 21,
        "StochD": 7,
        "StochSlow": 7,
        "OsmaFast": 8,
        "OsmaSlow": 17,
        "OsmaSignal": 9,
        "BBPeriod": 167,
        "BBDev": 1.8,
        "ATRPeriod1": 200,
        "ATRPeriod2": 55,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 20)),
        lot_value=float(payload.get("lot_value", 100.0)),
        description=payload.get("description", "XAU SQX Stochastic/OsMA/Bollinger family."),
        indicators=[
            IndicatorSpec("stoch", "sq_stochastic", {"high": "high", "low": "low", "close": "close", "k_period": {"param": "StochK"}, "d_period": {"param": "StochD"}, "slowing": {"param": "StochSlow"}, "ma_method": "sma", "price_mode": "lowhigh"}, outputs={"main": "stoch_main"}),
            IndicatorSpec("osma", "osma", {"open_": "open", "high": "high", "low": "low", "close": "close", "fast_period": {"param": "OsmaFast"}, "slow_period": {"param": "OsmaSlow"}, "signal_period": {"param": "OsmaSignal"}, "mode": 0}),
            IndicatorSpec("bb", "bollinger_bands", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "BBPeriod"}, "deviations": {"param": "BBDev"}, "mode": 1}, outputs={"upper": "bb_upper", "lower": "bb_lower"}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
        ],
        series=[
            SeriesSpec("long_signal", '_compare_window(df["stoch_main"], df["osma"], 6, 5, True, True) & (df["open"].shift(3) < df["bb_upper"].shift(3)) & (df["open"].shift(2) > df["bb_upper"].shift(3))'),
            SeriesSpec("short_signal", '_compare_window(df["stoch_main"], df["osma"], 6, 5, True, False) & (df["open"].shift(3) > df["bb_lower"].shift(3)) & (df["open"] < df["bb_lower"].shift(3))'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="xau_long",
                side="long",
                order_type="market",
                when='bool(df["long_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open * (1.0 - 0.008)',
                take_profit='ctx.open * (1.0 + 0.015)',
                trail_dist='70.0',
                trail_activation='4.0 * float(df["atr"].iloc[i - 1])',
                exit_after_bars=36,
                comment="sqx_xau_long",
            ),
            EntryRuleSpec(
                name="xau_short",
                side="short",
                order_type="market",
                when='bool(df["short_signal"].iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open * (1.0 + 0.010)',
                take_profit='ctx.open * (1.0 - 0.046)',
                trail_dist='2.7 * float(df["atr_2"].iloc[i - 1])',
                trail_activation='70.0',
                comment="sqx_xau_short",
            ),
        ],
    )
