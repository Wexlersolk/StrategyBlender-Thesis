from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_DIR = ROOT / "strategies" / "specs"
ENGINE_STRATEGY_DIR = ROOT / "strategies" / "generated"
PRESET_DIR = ROOT / "config" / "strategy_presets"

SUPPORTED_INDICATORS = {
    "ema": "ema",
    "sma": "sma",
    "wma": "wma",
    "smma": "smma",
    "osma": "osma",
    "rsi": "rsi",
    "sq_awesome_oscillator": "sq_awesome_oscillator",
    "bollinger_bands": "bollinger_bands",
    "select_price": "select_price",
    "sq_adx": "sq_adx",
    "sq_atr": "sq_atr",
    "sq_ema": "ema",
    "sq_sma": "sma",
    "sq_wma": "wma",
    "sq_smma": "smma",
    "sq_bb_width_ratio": "sq_bb_width_ratio",
    "sq_fibo": "sq_fibo",
    "sq_fractal": "sq_fractal",
    "sq_heiken_ashi": "sq_heiken_ashi",
    "sq_highest": "sq_highest",
    "sq_hma": "sq_hma",
    "sq_hull_moving_average": "sq_hull_moving_average",
    "sq_ichimoku": "sq_ichimoku",
    "sq_kama": "sq_kama",
    "sq_keltner_channel": "sq_keltner_channel",
    "sq_laguerre_rsi": "sq_laguerre_rsi",
    "sq_linreg": "sq_linreg",
    "sq_lowest": "sq_lowest",
    "sq_momentum": "sq_momentum",
    "sq_parabolic_sar": "sq_parabolic_sar",
    "sq_pivots": "sq_pivots",
    "sq_session_ohlc": "sq_session_ohlc",
    "sq_stochastic": "sq_stochastic",
    "sq_ulcer_index": "sq_ulcer_index",
    "sq_vwap": "sq_vwap",
    "sq_wave_trend": "sq_wave_trend",
    "sq_wpr": "sq_wpr",
    "sq_qqe": "sq_qqe",
    "SqADX": "sq_adx",
    "SqATR": "sq_atr",
    "SqEMA": "ema",
    "SqSMA": "sma",
    "SqWMA": "wma",
    "SqSMMA": "smma",
    "SqAwesomeOscillator": "sq_awesome_oscillator",
    "SqBBWidthRatio": "sq_bb_width_ratio",
    "SqFibo": "sq_fibo",
    "SqFractal": "sq_fractal",
    "SqHeikenAshi": "sq_heiken_ashi",
    "SqHighest": "sq_highest",
    "SqHMA": "sq_hma",
    "SqHullMovingAverage": "sq_hull_moving_average",
    "SqIchimoku": "sq_ichimoku",
    "SqKAMA": "sq_kama",
    "SqKeltnerChannel": "sq_keltner_channel",
    "SqLaguerreRSI": "sq_laguerre_rsi",
    "SqLinReg": "sq_linreg",
    "SqLowest": "sq_lowest",
    "SqMomentum": "sq_momentum",
    "SqParabolicSAR": "sq_parabolic_sar",
    "SqPivots": "sq_pivots",
    "SqRSI": "rsi",
    "SqSessionOHLC": "sq_session_ohlc",
    "SqStochastic": "sq_stochastic",
    "SqUlcerIndex": "sq_ulcer_index",
    "SqVWAP": "sq_vwap",
    "SqWaveTrend": "sq_wave_trend",
    "SqWPR": "sq_wpr",
}

SERIES_ARG_RENDERERS = {
    "series": lambda value: f'df[{value!r}]',
    "open_": lambda value: f'df[{value!r}]',
    "high": lambda value: f'df[{value!r}]',
    "low": lambda value: f'df[{value!r}]',
    "close": lambda value: f'df[{value!r}]',
    "volume": lambda value: f'df[{value!r}]',
    "df": lambda _value: "df",
}

COMPUTE_ALLOWED_NAMES = {
    "df",
    "self",
    "pd",
    "np",
    "abs",
    "min",
    "max",
    "int",
    "float",
    "bool",
    "str",
    "sma",
    "wma",
    "_count_compare",
    "_cross_above",
    "_cross_below",
    "_falling",
    "_rising",
    "_compare_window",
    "_sq_count_compare",
    "_sq_lower_percentile",
    "_hhmm",
    "_in_time_window",
}

ON_BAR_ALLOWED_NAMES = COMPUTE_ALLOWED_NAMES | {
    "ctx",
    "i",
}

@dataclass
class IndicatorSpec:
    name: str
    kind: str
    args: dict[str, Any]
    outputs: dict[str, str] | None = None

@dataclass
class SeriesSpec:
    name: str
    expression: str

@dataclass
class EntryRuleSpec:
    name: str
    side: str
    order_type: str
    when: str
    lots: str
    stop_loss: str
    take_profit: str
    price: str | None = None
    expiry_bars: int = 1
    comment: str = ""
    trail_dist: str | None = None
    trail_activation: str | None = None
    exit_after_bars: int | str | None = None

@dataclass
class ExitRuleSpec:
    name: str
    when: str
    action: str = "close_all"

@dataclass
class StrategySpec:
    name: str
    symbol: str
    timeframe: str
    params: dict[str, Any] = field(default_factory=dict)
    indicators: list[IndicatorSpec] = field(default_factory=list)
    series: list[SeriesSpec] = field(default_factory=list)
    entries: list[EntryRuleSpec] = field(default_factory=list)
    exits: list[ExitRuleSpec] = field(default_factory=list)
    min_bars: int = 0
    lot_value: float = 1.0
    bar_time_offset_hours: float = 0.0
    allow_entries_when_position_open: bool = False
    description: str = ""

@dataclass
class CompiledStrategy:
    spec: StrategySpec
    strategy_slug: str
    strategy_class: str
    strategy_module: str
    strategy_path: str
    spec_path: str
    source: str

@dataclass
class StrategyTemplate:
    name: str
    description: str
    build: Any
    family: str = "general"
    regime: str = ""
    supported_symbols: tuple[str, ...] = ()
    supported_timeframes: tuple[str, ...] = ()
    preferred_timeframes: tuple[str, ...] = ()
    sort_order: int = 100


TEMPLATE_REGISTRY: dict[str, StrategyTemplate] = {}


def register_template(
    name: str,
    description: str,
    family: str = "general",
    regime: str = "",
    supported_symbols: tuple[str, ...] = (),
    supported_timeframes: tuple[str, ...] = (),
    preferred_timeframes: tuple[str, ...] = (),
    sort_order: int = 100,
):
    def decorator(build_func: Any):
        template = StrategyTemplate(
            name=name,
            description=description,
            build=build_func,
            family=family,
            regime=regime,
            supported_symbols=supported_symbols,
            supported_timeframes=supported_timeframes,
            preferred_timeframes=preferred_timeframes,
            sort_order=sort_order,
        )
        TEMPLATE_REGISTRY[name] = template
        return build_func

    return decorator
