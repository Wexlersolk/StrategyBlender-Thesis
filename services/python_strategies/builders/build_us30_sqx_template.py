from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_us30_wpr_stoch",
    description="US30 mean-reversion using WPR and Stochastic.",
    family="index_reversion",
    regime="Index mean-reversion",
    supported_symbols=("US30.cash", "US100.cash"),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=20
)
def build_us30_sqx_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "WPRPeriod": 75,
        "StochK": 14,
        "StochD": 3,
        "StochSlow": 3,
        "HighestPeriod": 105,
        "LowestPeriod": 105,
        "ATRPeriod1": 14,
        "ATRPeriod2": 29,
        "mmLots": 1.0,
        "StopLossCoef1": 2.0,
        "ProfitTargetCoef1": 2.5,
        "StopLossCoef2": 2.0,
        "ProfitTargetCoef2": 2.5,
        "TrailingStopCoef1": 1.0,
        "MaxDistancePct": 6.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    long_window = int(payload.get("wpr_quantile_window", 250))
    long_shift = int(payload.get("wpr_shift", 10))
    short_bars = int(payload.get("short_falling_bars", 12))
    short_shift = int(payload.get("short_falling_shift", 3))
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=max(40, long_window),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "US30 SQX WPR/Stochastic breakout family."),
        indicators=[
            IndicatorSpec("stoch", "sq_stochastic", {"high": "high", "low": "low", "close": "close", "k_period": {"param": "StochK"}, "d_period": {"param": "StochD"}, "slowing": {"param": "StochSlow"}, "ma_method": "wma", "price_mode": "lowhigh"}, outputs={"signal": "stoch_signal"}),
            IndicatorSpec("wpr", "sq_wpr", {"high": "high", "low": "low", "close": "close", "period": {"param": "WPRPeriod"}}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 0}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 0}),
        ],
        series=[
            SeriesSpec("wpr_ref", f'df["wpr"].shift({long_shift})'),
            SeriesSpec("long_signal", f'df["wpr_ref"] <= df["wpr_ref"].rolling({long_window}, min_periods={long_window}).quantile(0.669)'),
            SeriesSpec("short_signal", f'_falling(df["stoch_signal"], {short_bars}, {short_shift})'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="us30_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and not bool(df["short_signal"].eq(True).iloc[i])',
                price='float(df["highest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest"].iloc[i - 1]) - float(self.p("StopLossCoef1")) * float(df["atr"].iloc[i - 1])',
                take_profit='float(df["highest"].iloc[i - 1]) + float(self.p("ProfitTargetCoef1")) * float(df["atr"].iloc[i - 1])',
                comment="sqx_us30_long",
                expiry_bars=25,
            ),
            EntryRuleSpec(
                name="us30_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and (abs(float(df["lowest"].iloc[i - 1]) - ctx.open) / max(abs(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))',
                price='float(df["lowest"].iloc[i - 1])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest"].iloc[i - 1]) + float(self.p("StopLossCoef2")) * float(df["atr"].iloc[i - 1])',
                take_profit='float(df["lowest"].iloc[i - 1]) - float(self.p("ProfitTargetCoef2")) * float(df["atr"].iloc[i - 1])',
                trail_dist='float(self.p("TrailingStopCoef1")) * float(df["atr_2"].iloc[i - 1])',
                comment="sqx_us30_short",
                expiry_bars=18,
            ),
        ],
    )
