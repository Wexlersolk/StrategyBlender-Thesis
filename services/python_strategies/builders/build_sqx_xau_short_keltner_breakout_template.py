from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_xau_short_keltner_breakout",
    description="XAU short Keltner-breakout family mined from SQX batch.",
    family="commodity_volatility_breakout",
    regime="Commodity volatility breakout",
    supported_symbols=("XAUUSD",),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=34
)
def build_sqx_xau_short_keltner_breakout_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "IndicatorMAPeriod1": 59,
        "StochasticKPeriod1": 14,
        "StochasticDPeriod1": 7,
        "StochasticSlowing1": 3,
        "KCerPeriod1": 20,
        "HighestPeriod": 370,
        "LowestPeriod": 370,
        "ATRTargetPeriod1": 19,
        "ATRStopPeriod1": 14,
        "ATRTargetPeriod2": 14,
        "ATRStopPeriod2": 14,
        "ProfitTargetCoef1": 3.5,
        "StopLossCoef1": 2.0,
        "ProfitTargetCoef2": 3.1,
        "StopLossCoef2": 2.4,
        "LongExpiryBars": 18,
        "ShortExpiryBars": 1,
        "TickSize": 0.01,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:00",
        "SignalTimeRangeTo": "23:59",
        "FridayExitTime": "22:38",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)

    direction_mode = _direction_mode(payload)
    short_keltner_band = str(payload.get("short_keltner_band", "middle")).strip().lower() or "middle"
    if short_keltner_band not in {"middle", "upper", "lower"}:
        raise ValueError(f"Unsupported short_keltner_band: {short_keltner_band}")
    short_band_series = {
        "middle": 'df["kc_middle"]',
        "upper": 'df["kc_upper"]',
        "lower": 'df["kc_lower"]',
    }[short_keltner_band]

    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_short_keltner_breakout_long",
                side="long",
                order_type="buy_stop",
                when='bool(df["long_signal"].eq(True).iloc[i]) and not bool(df["short_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["highest_level"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["highest_level"].iloc[i]) - (float(self.p("StopLossCoef1")) * float(df["atr_stop_1"].iloc[i]))',
                take_profit='float(df["highest_level"].iloc[i]) + (float(self.p("ProfitTargetCoef1")) * float(df["atr_target_1"].iloc[i]))',
                expiry_bars=int(params.get("LongExpiryBars", 18)),
                comment="sqx_xau_short_keltner_breakout_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="sqx_xau_short_keltner_breakout_short",
                side="short",
                order_type="sell_stop",
                when='bool(df["short_signal"].eq(True).iloc[i]) and not bool(df["long_signal"].eq(True).iloc[i]) and _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
                price='float(df["lowest_level"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='float(df["lowest_level"].iloc[i]) + (float(self.p("StopLossCoef2")) * float(df["atr_stop_2"].iloc[i]))',
                take_profit='float(df["lowest_level"].iloc[i]) - (float(self.p("ProfitTargetCoef2")) * float(df["atr_target_2"].iloc[i]))',
                expiry_bars=int(params.get("ShortExpiryBars", 1)),
                comment="sqx_xau_short_keltner_breakout_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 900)),
        lot_value=float(payload.get("lot_value", 100.0)),
        bar_time_offset_hours=float(payload.get("bar_time_offset_hours", 6.0)),
        description=payload.get(
            "description",
            "Native XAU H1 family mined from Strategy 5.3.86, with WMA/Stochastic long bias, Keltner-rising short filter, 370-bar stop entries, and ultra-short short expiry.",
        ),
        indicators=[
            IndicatorSpec(
                "stoch",
                "sq_stochastic",
                {
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "k_period": {"param": "StochasticKPeriod1"},
                    "d_period": {"param": "StochasticDPeriod1"},
                    "slowing": {"param": "StochasticSlowing1"},
                    "ma_method": "sma",
                    "price_mode": "lowhigh",
                },
                outputs={"main": "stoch_main", "signal": "stoch_signal"},
            ),
            IndicatorSpec(
                "kc",
                "sq_keltner_channel",
                {
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "period": {"param": "KCerPeriod1"},
                    "multiplier": 1.5,
                },
                outputs={"middle": "kc_middle", "upper": "kc_upper", "lower": "kc_lower"},
            ),
            IndicatorSpec(
                "highest_level",
                "sq_highest",
                {
                    "open_": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "period": {"param": "HighestPeriod"},
                    "mode": 0,
                },
            ),
            IndicatorSpec(
                "lowest_level",
                "sq_lowest",
                {
                    "open_": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "period": {"param": "LowestPeriod"},
                    "mode": 0,
                },
            ),
            IndicatorSpec("atr_target_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRTargetPeriod1"}}),
            IndicatorSpec("atr_stop_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRStopPeriod1"}}),
            IndicatorSpec("atr_target_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRTargetPeriod2"}}),
            IndicatorSpec("atr_stop_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRStopPeriod2"}}),
        ],
        series=[
            SeriesSpec("stoch_signal_ma", 'wma(df["stoch_signal"], int(self.p("IndicatorMAPeriod1")))'),
            SeriesSpec("long_signal", 'df["stoch_signal"].shift(3).round(6) > df["stoch_signal_ma"].shift(3).round(6)'),
            SeriesSpec(
                "short_signal",
                f'({short_band_series}.shift(3).round(6) > {short_band_series}.shift(4).round(6)) & ({short_band_series}.shift(4).round(6) > {short_band_series}.shift(5).round(6))',
            ),
        ],
        exits=[
            ExitRuleSpec(
                "friday_exit",
                'ctx.has_position and int(ctx.time.dayofweek) == 4 and _hhmm(ctx.time) >= (int(str(self.p("FridayExitTime"))[:2]) * 100 + int(str(self.p("FridayExitTime"))[3:]))',
            ),
        ],
        entries=entries,
    )
