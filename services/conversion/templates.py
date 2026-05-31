from __future__ import annotations

from engine.indicators import is_indicator_supported
from services.conversion.parser import (
    _extract_bool_input,
    _extract_custom_indicator_names,
    _extract_ibands_spec,
    _extract_ima_spec,
    _extract_indicator_spec,
    _extract_iosma_spec,
    _extract_string_input,
    _find_icustom_args,
    _find_int_literal,
    _find_param,
    _indicator_port_available,
    _resolve_mql_float,
    _resolve_mql_numeric,
)
from services.conversion.utils import PRICE_MODE_MAP, _infer_lot_value


def _build_us30_pattern_source(
    strategy_name: str,
    class_name: str,
    symbol: str,
    timeframe: str,
    params: dict,
    mql_source: str,
) -> tuple[str, list[str]]:
    warnings = [
        "Generated with a StrategyQuant pattern builder for WPR/Stochastic entries.",
    ]
    wpr_period = _extract_indicator_spec(mql_source, "SqWPR", "WILLIAMSPR_1", (75,))[0]
    stoch_k, stoch_d, stoch_slow = _extract_indicator_spec(mql_source, "SqStochastic", "STOCHASTIC_1", (14, 3, 3))
    highest_period, highest_price_mode = _extract_indicator_spec(
        mql_source, "SqHighest", "HIGHEST_1", (105, PRICE_MODE_MAP["PRICE_CLOSE"])
    )
    lowest_period, lowest_price_mode = _extract_indicator_spec(
        mql_source, "SqLowest", "LOWEST_1", (105, PRICE_MODE_MAP["PRICE_CLOSE"])
    )
    atr1_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_1", (14,))[0]
    atr2_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_2", (29,))[0]
    lots = float(_find_param(params, "mmlots", "lots", default=1.0))
    signal_from = _extract_string_input(mql_source, "SignalTimeRangeFrom", "00:00")
    signal_to = _extract_string_input(mql_source, "SignalTimeRangeTo", "23:59")
    friday_exit_time = _extract_string_input(mql_source, "FridayExitTime", "23:59")
    exit_on_friday = _extract_bool_input(mql_source, "ExitOnFriday", False)
    exit_at_end_of_range = _extract_bool_input(mql_source, "ExitAtEndOfRange", False)
    max_distance_pct = float(_find_param(params, "MaxDistanceFromMarketPct".lower(), "maxdistancefrommarketpct", default=6.0))
    trade_in_session = _extract_bool_input(mql_source, "tradeInSessionHoursOnly", False)
    src = f'''"""
Auto-generated engine strategy from MT5 source.
Uses a StrategyQuant-specific pattern for WPR/Stochastic entries.
"""

from __future__ import annotations

import pandas as pd

from engine.base_strategy import BaseStrategy, BarContext
from engine.indicators import sq_atr, sq_highest, sq_lowest, sq_stochastic, sq_wpr


def _hhmm(ts: pd.Timestamp) -> int:
    return ts.hour * 100 + ts.minute


def _in_time_window(ts: pd.Timestamp, start: str, end: str) -> bool:
    start_hhmm = int(start[:2]) * 100 + int(start[3:])
    end_hhmm = int(end[:2]) * 100 + int(end[3:])
    current = _hhmm(ts)
    if start_hhmm <= end_hhmm:
        return start_hhmm <= current < end_hhmm
    return current >= start_hhmm or current < end_hhmm


def _falling_signal(series: pd.Series, bars: int, shift: int) -> pd.Series:
    ref = series.shift(shift)
    delta = ref.diff()
    return delta.rolling(bars, min_periods=bars).apply(
        lambda values: float((values < 0).all()),
        raw=True,
    ).fillna(0.0) > 0.5


class {class_name}(BaseStrategy):
    name = {strategy_name!r}
    symbol = {symbol!r}
    timeframe = {timeframe!r}
    lot_value = {_infer_lot_value(symbol)!r}
    params = {params!r}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = sq_stochastic(
            df["high"],
            df["low"],
            df["close"],
            {int(stoch_k)},
            {int(stoch_d)},
            {int(stoch_slow)},
            ma_method="wma",
            price_mode="lowhigh",
        )
        df["stoch_signal"] = stoch["signal"]
        df["wpr"] = sq_wpr(df["high"], df["low"], df["close"], {int(wpr_period)})
        df["atr"] = sq_atr(df["high"], df["low"], df["close"], {int(atr1_period)})
        df["atr_2"] = sq_atr(df["high"], df["low"], df["close"], {int(atr2_period)})
        df["highest"] = sq_highest(df["open"], df["high"], df["low"], df["close"], {int(highest_period)}, {int(highest_price_mode)})
        df["lowest"] = sq_lowest(df["open"], df["high"], df["low"], df["close"], {int(lowest_period)}, {int(lowest_price_mode)})
        wpr_ref = df["wpr"].shift(10)
        df["long_signal"] = wpr_ref <= wpr_ref.rolling(995, min_periods=995).quantile(0.669)
        df["short_signal"] = _falling_signal(df["stoch_signal"], 35, 7)
        return df

    def on_start(self, df: pd.DataFrame):
        self._next_trail_dist = 0.0
        self._next_trail_activation = 0.0
        self._next_exit_after_bars = 0

    def on_bar(self, ctx: BarContext):
        i = ctx.bar_index
        if i < 40:
            return

        df = ctx.df
        if {str(exit_on_friday)} and ctx.time.weekday() == 4 and _hhmm(ctx.time) >= {int(friday_exit_time[:2]) * 100 + int(friday_exit_time[3:])}:
            if ctx.has_position:
                ctx.close_all()
            if ctx.has_pending:
                ctx.cancel_pending()
            return
        if {str(exit_at_end_of_range)} and ctx.has_position and not _in_time_window(ctx.time, "{signal_from}", "{signal_to}"):
            ctx.close_all()
            return
        if ctx.has_position or ctx.has_pending:
            return
        if {str(trade_in_session)} and ctx.time.weekday() >= 5:
            return
        lots = {lots}
        if bool(df["long_signal"].iloc[-1]) and not bool(df["short_signal"].iloc[-1]):
            entry = float(df["highest"].iloc[-1])
            atr1 = float(df["atr"].iloc[-1])
            if any(v != v or v <= 0 for v in [entry, atr1]):
                return
            self._next_trail_dist = 0.0
            self._next_trail_activation = 0.0
            self._next_exit_after_bars = 0
            ctx.buy_stop(
                price=entry,
                sl=entry - float(self.p("StopLossCoef1")) * atr1,
                tp=entry + float(self.p("ProfitTargetCoef1")) * atr1,
                lots=lots,
                expiry_bars=161,
                comment="sq_long",
            )
        elif bool(df["short_signal"].iloc[-1]) and not bool(df["long_signal"].iloc[-1]):
            entry = float(df["lowest"].iloc[-1])
            atr1 = float(df["atr"].iloc[-1])
            atr2 = float(df["atr_2"].iloc[-1])
            if any(v != v or v <= 0 for v in [entry, atr1, atr2]):
                return
            if abs(entry - ctx.open) / max(abs(ctx.open), 1e-9) * 100.0 > {max_distance_pct}:
                return
            self._next_trail_dist = float(self.p("TrailingStopCoef1")) * atr2
            self._next_trail_activation = 0.0
            self._next_exit_after_bars = 0
            ctx.sell_stop(
                price=entry,
                sl=entry + float(self.p("StopLossCoef2")) * atr1,
                tp=entry - float(self.p("ProfitTargetCoef2")) * atr1,
                lots=lots,
                expiry_bars=111,
                comment="sq_short",
            )
'''
    return src, warnings


def _build_xau_pattern_source(
    strategy_name: str,
    class_name: str,
    symbol: str,
    timeframe: str,
    params: dict,
    mql_source: str,
) -> tuple[str, list[str]]:
    warnings = [
        "Generated with a StrategyQuant pattern builder for Stochastic/OsMA/Bollinger entries.",
    ]
    stoch_k, stoch_d, stoch_slow = _extract_indicator_spec(mql_source, "SqStochastic", "STOCHASTIC_1", (21, 7, 7))
    osma_fast, osma_slow, osma_signal, osma_mode = _extract_iosma_spec(
        mql_source, "OSMA_1", (8, 17, 9, PRICE_MODE_MAP["PRICE_CLOSE"])
    )
    bb_period, bb_dev, bb_mode = _extract_ibands_spec(
        mql_source, "BOLLINGERBANDS_1", (167, 1.8, PRICE_MODE_MAP["PRICE_OPEN"])
    )
    atr1_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_1", (200,))[0]
    atr2_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_2", (55,))[0]
    lots = float(_find_param(params, "mmlots", "lots", default=1.0))
    signal_from = _extract_string_input(mql_source, "SignalTimeRangeFrom", "00:00")
    signal_to = _extract_string_input(mql_source, "SignalTimeRangeTo", "23:59")
    friday_exit_time = _extract_string_input(mql_source, "FridayExitTime", "23:59")
    exit_on_friday = _extract_bool_input(mql_source, "ExitOnFriday", False)
    exit_at_end_of_range = _extract_bool_input(mql_source, "ExitAtEndOfRange", False)
    trade_in_session = _extract_bool_input(mql_source, "tradeInSessionHoursOnly", False)
    src = f'''"""
Auto-generated engine strategy from MT5 source.
Uses a StrategyQuant-specific pattern for XAU market entries.
"""

from __future__ import annotations

import pandas as pd

from engine.base_strategy import BaseStrategy, BarContext
from engine.indicators import bollinger_bands, osma, sq_atr, sq_stochastic


def _hhmm(ts: pd.Timestamp) -> int:
    return ts.hour * 100 + ts.minute


def _in_time_window(ts: pd.Timestamp, start: str, end: str) -> bool:
    start_hhmm = int(start[:2]) * 100 + int(start[3:])
    end_hhmm = int(end[:2]) * 100 + int(end[3:])
    current = _hhmm(ts)
    if start_hhmm <= end_hhmm:
        return start_hhmm <= current < end_hhmm
    return current >= start_hhmm or current < end_hhmm


def _compare_window(left: pd.Series, right: pd.Series, bars: int, shift: int, allow_same: bool, greater: bool) -> pd.Series:
    lhs = left.shift(shift)
    rhs = right.shift(shift)
    if greater:
        ok = lhs >= rhs if allow_same else lhs > rhs
        strict = lhs > rhs
    else:
        ok = lhs <= rhs if allow_same else lhs < rhs
        strict = lhs < rhs
    return ok.rolling(bars, min_periods=bars).sum().eq(bars) & strict.rolling(bars, min_periods=bars).sum().gt(0)


class {class_name}(BaseStrategy):
    name = {strategy_name!r}
    symbol = {symbol!r}
    timeframe = {timeframe!r}
    lot_value = {_infer_lot_value(symbol)!r}
    params = {params!r}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = sq_stochastic(df["high"], df["low"], df["close"], {int(stoch_k)}, {int(stoch_d)}, {int(stoch_slow)}, ma_method="sma", price_mode="lowhigh")
        bb = bollinger_bands(df["open"], df["high"], df["low"], df["close"], {int(bb_period)}, {float(bb_dev)}, {int(bb_mode)})
        df["stoch_main"] = stoch["main"]
        df["osma"] = osma(df["open"], df["high"], df["low"], df["close"], {int(osma_fast)}, {int(osma_slow)}, {int(osma_signal)}, {int(osma_mode)})
        df["bb_upper"] = bb["upper"]
        df["bb_lower"] = bb["lower"]
        df["atr"] = sq_atr(df["high"], df["low"], df["close"], {int(atr1_period)})
        df["atr_2"] = sq_atr(df["high"], df["low"], df["close"], {int(atr2_period)})
        df["long_signal"] = _compare_window(df["stoch_main"], df["osma"], 6, 5, True, True) & (df["open"].shift(3) < df["bb_upper"].shift(3)) & (df["open"].shift(2) > df["bb_upper"].shift(3))
        df["short_signal"] = _compare_window(df["stoch_main"], df["osma"], 6, 5, True, False) & (df["open"].shift(3) > df["bb_lower"].shift(3)) & (df["open"] < df["bb_lower"].shift(3))
        return df

    def on_start(self, df: pd.DataFrame):
        self._next_trail_dist = 0.0
        self._next_trail_activation = 0.0
        self._next_exit_after_bars = 0

    def on_bar(self, ctx: BarContext):
        i = ctx.bar_index
        if i < 10:
            return

        df = ctx.df
        if {str(exit_on_friday)} and ctx.time.weekday() == 4 and _hhmm(ctx.time) >= {int(friday_exit_time[:2]) * 100 + int(friday_exit_time[3:])}:
            if ctx.has_position:
                ctx.close_all()
            if ctx.has_pending:
                ctx.cancel_pending()
            return
        if {str(exit_at_end_of_range)} and ctx.has_position and not _in_time_window(ctx.time, "{signal_from}", "{signal_to}"):
            ctx.close_all()
            return
        if ctx.has_position or ctx.has_pending:
            return
        if {str(trade_in_session)} and ctx.time.weekday() >= 5:
            return
        if not _in_time_window(ctx.time, "{signal_from}", "{signal_to}"):
            return

        lots = {lots}
        if bool(df["long_signal"].iloc[-1]):
            open_price = ctx.open
            atr1 = float(df["atr"].iloc[-1])
            if atr1 != atr1 or atr1 <= 0:
                return
            self._next_trail_dist = 70.0
            self._next_trail_activation = 4.0 * atr1
            self._next_exit_after_bars = 36
            ctx.buy_market(
                sl=open_price * (1.0 - 0.008),
                tp=open_price * (1.0 + 0.015),
                lots=lots,
                comment="sq_long",
            )
        elif bool(df["short_signal"].iloc[-1]):
            atr2 = float(df["atr_2"].iloc[-1])
            if atr2 != atr2 or atr2 <= 0:
                return
            self._next_trail_dist = 2.7 * atr2
            self._next_trail_activation = 70.0
            self._next_exit_after_bars = 0
            ctx.sell_market(
                sl=ctx.open * (1.0 + 0.010),
                tp=ctx.open * (1.0 - 0.046),
                lots=lots,
                comment="sq_short",
            )
'''
    return src, warnings


def _build_usdjpy_pattern_source(
    strategy_name: str,
    class_name: str,
    symbol: str,
    timeframe: str,
    params: dict,
    mql_source: str,
) -> tuple[str, list[str]]:
    warnings = [
        "Generated with a StrategyQuant pattern builder for EMA/VWAP/WaveTrend entries.",
        "USDJPY uses exact-ish StrategyQuant count/cross helpers, but intrabar H4 time-window behavior is still approximated.",
    ]
    ema_period, ema_mode = _extract_ima_spec(mql_source, "EMA_1", (20, PRICE_MODE_MAP["PRICE_TYPICAL"]))
    vwap_period = _extract_indicator_spec(mql_source, "SqVWAP", "VWAP_1", (77,))[0]
    wt_channel, wt_average = _extract_indicator_spec(mql_source, "SqWaveTrend", "WAVETREND_1", (9, 60))
    highest_period, highest_price_mode = _extract_indicator_spec(
        mql_source, "SqHighest", "HIGHEST_1", (20, PRICE_MODE_MAP["PRICE_LOW"])
    )
    lowest_period, lowest_price_mode = _extract_indicator_spec(
        mql_source, "SqLowest", "LOWEST_1", (20, PRICE_MODE_MAP["PRICE_HIGH"])
    )
    bb1_args = _find_icustom_args(mql_source, "SqBBWidthRatio", "BBWIDTHRATIO_1") or ["64", "0.7", "PRICE_OPEN"]
    bb2_args = _find_icustom_args(mql_source, "SqBBWidthRatio", "BBWIDTHRATIO_2") or ["51", "0.7", "PRICE_OPEN"]
    bb1_period = _resolve_mql_numeric(bb1_args[0], 64)
    bb1_dev = _resolve_mql_float(bb1_args[1], 0.7)
    bb1_mode = _resolve_mql_numeric(bb1_args[2], PRICE_MODE_MAP["PRICE_OPEN"])
    bb2_period = _resolve_mql_numeric(bb2_args[0], 51)
    bb2_dev = _resolve_mql_float(bb2_args[1], 0.7)
    bb2_mode = _resolve_mql_numeric(bb2_args[2], PRICE_MODE_MAP["PRICE_OPEN"])
    atr1_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_1", (19,))[0]
    atr2_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_2", (14,))[0]
    atr3_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_3", (50,))[0]
    atr4_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_4", (40,))[0]
    lots = float(_find_param(params, "mmlots", "lots", default=1.0))
    price_entry_mult = float(_find_param(params, "PriceEntryMult1".lower(), "priceentrymult1", default=0.3))
    signal_from = _extract_string_input(mql_source, "SignalTimeRangeFrom", "00:00")
    signal_to = _extract_string_input(mql_source, "SignalTimeRangeTo", "23:59")
    friday_exit_time = _extract_string_input(mql_source, "FridayExitTime", "23:59")
    exit_on_friday = _extract_bool_input(mql_source, "ExitOnFriday", False)
    exit_at_end_of_range = _extract_bool_input(mql_source, "ExitAtEndOfRange", False)
    max_distance_pct = float(_find_param(params, "MaxDistanceFromMarketPct".lower(), "maxdistancefrommarketpct", default=6.0))
    trade_in_session = _extract_bool_input(mql_source, "tradeInSessionHoursOnly", False)
    src = f'''"""
Auto-generated engine strategy from MT5 source.
Uses a StrategyQuant-specific pattern for USDJPY breakout entries.
"""

from __future__ import annotations

import pandas as pd

from engine.base_strategy import BaseStrategy, BarContext
from engine.indicators import ema, select_price, sma, sq_atr, sq_bb_width_ratio, sq_highest, sq_hull_moving_average, sq_lowest, sq_session_ohlc, sq_vwap, sq_wave_trend, wma


def _hhmm(ts: pd.Timestamp) -> int:
    return ts.hour * 100 + ts.minute


def _in_time_window(ts: pd.Timestamp, start: str, end: str) -> bool:
    start_hhmm = int(start[:2]) * 100 + int(start[3:])
    end_hhmm = int(end[:2]) * 100 + int(end[3:])
    current = _hhmm(ts)
    if start_hhmm <= end_hhmm:
        return start_hhmm <= current < end_hhmm
    return current >= start_hhmm or current < end_hhmm


def _sq_count_compare(
    left: pd.Series,
    right: pd.Series,
    bars: int,
    shift: int,
    *,
    greater: bool,
    not_strict: bool,
    rounding: int = 5,
) -> pd.Series:
    comparisons = []
    strict_hits = []
    for offset in range(bars):
        lhs = left.shift(shift + offset).round(rounding)
        rhs = right.shift(shift + offset).round(rounding)
        if greater:
            comparisons.append(lhs >= rhs if not_strict else lhs > rhs)
            strict_hits.append(lhs > rhs)
        else:
            comparisons.append(lhs <= rhs if not_strict else lhs < rhs)
            strict_hits.append(lhs < rhs)
    all_ok = comparisons[0]
    any_strict = strict_hits[0]
    for item in comparisons[1:]:
        all_ok = all_ok & item
    for item in strict_hits[1:]:
        any_strict = any_strict | item
    return all_ok & any_strict


def _ma_by_type(series: pd.Series, period: int, ma_type: int) -> pd.Series:
    if ma_type == 1:
        return sma(series, period)
    if ma_type == 2:
        return ema(series, period)
    if ma_type == 3:
        return wma(series, period)
    if ma_type == 4:
        return sq_hull_moving_average(series, period)
    return sma(series, period)


def _sq_indicator_cross(series: pd.Series, period: int, ma_type: int, shift: int, *, above: bool) -> pd.Series:
    ref = series.shift(shift).round(6)
    ma = _ma_by_type(ref, period, ma_type).round(6)
    if above:
        return (ref.shift(1) <= ma.shift(1)) & (ref > ma)
    return (ref.shift(1) >= ma.shift(1)) & (ref < ma)


class {class_name}(BaseStrategy):
    name = {strategy_name!r}
    symbol = {symbol!r}
    timeframe = {timeframe!r}
    lot_value = {_infer_lot_value(symbol)!r}
    params = {params!r}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        ema_source = select_price(df["open"], df["high"], df["low"], df["close"], {int(ema_mode)})
        wt = sq_wave_trend(df["high"], df["low"], df["close"], {int(wt_channel)}, {int(wt_average)})
        bb_source_1 = select_price(df["open"], df["high"], df["low"], df["close"], {int(bb1_mode)})
        bb_source_2 = select_price(df["open"], df["high"], df["low"], df["close"], {int(bb2_mode)})
        df["ema_1"] = ema(ema_source, {int(ema_period)})
        df["vwap"] = sq_vwap(df["open"], df["high"], df["low"], df["close"], df["volume"], {int(vwap_period)})
        df["wavetrend"] = wt["main"]
        df["highest"] = sq_highest(df["open"], df["high"], df["low"], df["close"], {int(highest_period)}, {int(highest_price_mode)})
        df["lowest"] = sq_lowest(df["open"], df["high"], df["low"], df["close"], {int(lowest_period)}, {int(lowest_price_mode)})
        df["bbwr_1"] = sq_bb_width_ratio(bb_source_1, {int(bb1_period)}, {float(bb1_dev)})
        df["bbwr_2"] = sq_bb_width_ratio(bb_source_2, {int(bb2_period)}, {float(bb2_dev)})
        df["atr"] = sq_atr(df["high"], df["low"], df["close"], {int(atr1_period)})
        df["atr_2"] = sq_atr(df["high"], df["low"], df["close"], {int(atr2_period)})
        df["atr_3"] = sq_atr(df["high"], df["low"], df["close"], {int(atr3_period)})
        df["atr_4"] = sq_atr(df["high"], df["low"], df["close"], {int(atr4_period)})
        df["session_low"] = sq_session_ohlc(df, 3, 12, 32, 4, 3, 2)
        df["long_entry_signal"] = _sq_count_compare(df["open"], df["ema_1"].shift(2), 5, 3, greater=False, not_strict=False)
        df["short_entry_signal"] = False
        df["long_exit_signal"] = _sq_indicator_cross(df["vwap"].shift(3), int(self.p("IndicatorCrsMAPrd1")), 1, 1, above=False) & (df["wavetrend"].shift(1) > 0)
        df["short_exit_signal"] = _sq_indicator_cross(df["session_low"], int(self.p("IndicatorCrsMAPrd2")), 2, 1, above=True)
        return df

    def on_start(self, df: pd.DataFrame):
        self._next_trail_dist = 0.0
        self._next_trail_activation = 0.0
        self._next_exit_after_bars = 0

    def on_bar(self, ctx: BarContext):
        i = ctx.bar_index
        if i < 8:
            return

        df = ctx.df
        if {str(exit_on_friday)} and ctx.time.weekday() == 4 and _hhmm(ctx.time) >= {int(friday_exit_time[:2]) * 100 + int(friday_exit_time[3:])}:
            if ctx.has_position:
                ctx.close_all()
            if ctx.has_pending:
                ctx.cancel_pending()
            return
        if {str(exit_at_end_of_range)} and ctx.has_position and not _in_time_window(ctx.time, "{signal_from}", "{signal_to}"):
            ctx.close_all()
            return
        if {str(trade_in_session)} and ctx.time.weekday() >= 5:
            return
        if ctx.has_long and bool(df["long_exit_signal"].iloc[-1]):
            ctx.close_all()
            return
        if ctx.has_short and bool(df["short_exit_signal"].iloc[-1]):
            ctx.close_all()
            return
        if ctx.has_position or ctx.has_pending:
            return
        lots = {lots}
        if bool(df["long_entry_signal"].iloc[-1]) and not bool(df["short_entry_signal"].iloc[-1]):
            entry = float(df["highest"].iloc[-2]) + {price_entry_mult} * float(df["bbwr_1"].iloc[-3])
            atr1 = float(df["atr"].iloc[-1])
            atr2 = float(df["atr_2"].iloc[-1])
            if any(v != v or v <= 0 for v in [entry, atr1, atr2]):
                return
            self._next_trail_dist = 0.0
            self._next_trail_activation = 0.0
            self._next_exit_after_bars = int(self.p("ExitAfterBars1"))
            ctx.buy_stop(
                price=entry,
                sl=entry - float(self.p("StopLossCoef1")) * atr2,
                tp=entry + float(self.p("ProfitTargetCoef1")) * atr1,
                lots=lots,
                expiry_bars=17,
                comment="sq_long",
            )
'''
    return src, warnings


def _build_engine_strategy_source(
    strategy_name: str,
    class_name: str,
    symbol: str,
    timeframe: str,
    params: dict,
    mql_source: str,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    lower_source = mql_source.lower()
    custom_indicators = _extract_custom_indicator_names(mql_source)

    if 'sqGetIndicatorValue(VWAP_1, 0, 3)' in mql_source and 'sqGetIndicatorValue(BBWIDTHRATIO_1, 0, 3)' in mql_source:
        return _build_usdjpy_pattern_source(strategy_name, class_name, symbol, timeframe, params, mql_source)
    if 'sqGetIndicatorValue(OSMA_1, 0, 3)' in mql_source and 'BOLLINGERBANDS_1' in mql_source:
        return _build_xau_pattern_source(strategy_name, class_name, symbol, timeframe, params, mql_source)
    if 'sqGetIndicatorValue(WILLIAMSPR_1, 0, 4)' in mql_source and 'sqIsFalling(STOCHASTIC_1, 35' in mql_source:
        return _build_us30_pattern_source(strategy_name, class_name, symbol, timeframe, params, mql_source)

    has_atr = (
        any("atr" in key.lower() for key in params)
        or "iatr(" in lower_source
        or "sqatr" in lower_source
        or "atr_" in lower_source
        or "sqgetindicatorvalue(atr_" in lower_source
    )
    has_ma = any(token in lower_source for token in ["ima(", "lwma", "ema", "sma", "wma"])
    has_ao = "iao(" in lower_source or "awesome" in lower_source or "\"ao\"" in lower_source

    fast_period = _find_param(
        params,
        "fast",
        "lwmaperiod",
        "mafast",
        "shortperiod",
        "quick",
        default=10,
    )
    slow_period = _find_param(
        params,
        "slow",
        "indicatorcrsmaprd",
        "maslow",
        "longperiod",
        default=max(int(float(fast_period)) * 3, 20),
    )

    lots = _find_param(params, "mmlots", "lots", "lot", default=1.0)
    stop_loss_coef = _find_param(params, "stoplosscoef", "stoploss", "sl", default=1.5)
    take_profit_coef = _find_param(params, "profittargetcoef", "takeprofit", "tp", default=2.0)
    highest_period = _find_param(params, "highest_period", "highest", default=20)
    lowest_period = _find_param(params, "lowest_period", "lowest", default=20)
    atr_period = _find_param(params, "atr1_period", "atr_period", "atr", default=None)
    if atr_period is None:
        atr_period = _find_int_literal(mql_source, r"#define\s+ATR_1\s+\d+\s+//iCustom\(NULL,\s*0,\s*\"SqATR\",\s*(\d+)\)", 14)
    atr_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_1", (int(float(atr_period)),))[0]
    atr2_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_2", (45,))[0]
    atr3_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_3", (14,))[0]
    atr4_period = _extract_indicator_spec(mql_source, "SqATR", "ATR_4", (100,))[0]
    highest_period, highest_price_mode = _extract_indicator_spec(
        mql_source,
        "SqHighest",
        "HIGHEST_1",
        (int(float(highest_period)), PRICE_MODE_MAP["PRICE_HIGH"]),
    )
    lowest_period, lowest_price_mode = _extract_indicator_spec(
        mql_source,
        "SqLowest",
        "LOWEST_1",
        (int(float(lowest_period)), PRICE_MODE_MAP["PRICE_LOW"]),
    )
    trailing_stop_1 = _find_param(params, "trailingstop1", default=0.0)
    trailing_activation_coef = _find_param(params, "trailingactcef1", "trailingactcoef1", default=0.0)
    trailing_stop_coef_1 = _find_param(params, "trailingstopcoef1", default=0.0)
    lot_value = _infer_lot_value(symbol)

    if not has_ma and not has_ao:
        warnings.append(
            "No recognizable MA/AO signal logic was found. Generated local strategy uses a fallback MA crossover."
        )
    if not has_atr:
        warnings.append(
            "No ATR-based risk parameters were found. Generated local strategy falls back to rolling volatility."
        )
    for indicator_name in custom_indicators:
        if not _indicator_port_available(indicator_name):
            warnings.append(f"{indicator_name} is referenced, but mine/Indicators/{indicator_name}.mq5 was not found.")
        if not is_indicator_supported(indicator_name):
            warnings.append(
                f"{indicator_name} is referenced by the EA, but no dedicated Python port exists yet."
            )

    src = f'''"""
Auto-generated engine strategy from MT5 source.
This is a heuristic local-backtest translation, not a one-to-one MQL5 port.
"""

from __future__ import annotations

import pandas as pd

from engine.base_strategy import BaseStrategy, BarContext
from engine.indicators import ema, sq_atr, sq_highest, sq_lowest, wma


class {class_name}(BaseStrategy):
    name = {strategy_name!r}
    symbol = {symbol!r}
    timeframe = {timeframe!r}
    lot_value = {lot_value!r}
    params = {params!r}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        lwma_period = max(int(self.p("_fast_period")), 2)
        ma_period = max(int(self.p("_slow_period")), lwma_period + 1)
        atr_period = max(int(self.p("_atr_period")), 2)
        atr2_period = max(int(self.p("_atr2_period")), 2)
        atr3_period = max(int(self.p("_atr3_period")), 2)
        atr4_period = max(int(self.p("_atr4_period")), 2)
        highest_period = max(int(self.p("_highest_period")), 2)
        lowest_period = max(int(self.p("_lowest_period")), 2)

        df["lwma"] = wma(df["close"], lwma_period)
        df["lwma_ma"] = ema(df["lwma"], ma_period)
        df["atr"] = sq_atr(df["high"], df["low"], df["close"], atr_period)
        df["atr_2"] = sq_atr(df["high"], df["low"], df["close"], atr2_period)
        df["atr_3"] = sq_atr(df["high"], df["low"], df["close"], atr3_period)
        df["atr_4"] = sq_atr(df["high"], df["low"], df["close"], atr4_period)
        df["highest"] = sq_highest(
            df["open"], df["high"], df["low"], df["close"], highest_period, int(self.p("_highest_price_mode"))
        )
        df["lowest"] = sq_lowest(
            df["open"], df["high"], df["low"], df["close"], lowest_period, int(self.p("_lowest_price_mode"))
        )
        midpoint = (df["high"] + df["low"]) / 2.0
        df["ao"] = midpoint.rolling(5).mean() - midpoint.rolling(34).mean()
        return df

    def on_start(self, df: pd.DataFrame):
        self._next_trail_dist = 0.0
        self._next_trail_activation = 0.0

    def on_bar(self, ctx: BarContext):
        if ctx.has_position or ctx.has_pending:
            return

        i = ctx.bar_index
        if i < 2:
            return

        df = ctx.df
        ao = df["ao"]
        lwma = df["lwma"]
        lwma_ma = df["lwma_ma"]
        lots = float(self.p("_lots"))

        long_signal = self.crosses_above(ao, 0.0, i)
        short_signal = self.crosses_below_series(lwma, lwma_ma, i)

        if long_signal and not short_signal:
            entry = float(df["highest"].iloc[-1])
            atr1 = float(df["atr"].iloc[-1])
            atr2 = float(df["atr_2"].iloc[-1])
            if any(v != v or v <= 0 for v in [entry, atr1, atr2]):
                return
            sl = entry - float(self.p("_stop_loss_coef")) * atr1
            tp = entry + float(self.p("_take_profit_coef")) * atr1
            self._next_trail_dist = float(self.p("_trailing_stop_1"))
            self._next_trail_activation = float(self.p("_trailing_activation_coef")) * atr2
            ctx.buy_stop(
                price=entry,
                sl=sl,
                tp=tp,
                lots=lots,
                expiry_bars=1,
                comment="generated_long",
            )

        elif short_signal and not long_signal:
            entry = float(df["lowest"].iloc[-1])
            atr3 = float(df["atr_3"].iloc[-1])
            atr1 = float(df["atr"].iloc[-1])
            atr4 = float(df["atr_4"].iloc[-1])
            if any(v != v or v <= 0 for v in [entry, atr3, atr1, atr4]):
                return
            sl = entry + float(self.p("_stop_loss_coef_2")) * atr3
            tp = entry - float(self.p("_take_profit_coef_2")) * atr1
            self._next_trail_dist = float(self.p("_trailing_stop_coef_1")) * atr4
            self._next_trail_activation = 0.0
            ctx.sell_stop(
                price=entry,
                sl=sl,
                tp=tp,
                lots=lots,
                expiry_bars=1,
                comment="generated_short",
            )


{class_name}.params.update({{
    "_fast_period": {int(float(fast_period))},
    "_slow_period": {int(float(slow_period))},
    "_atr_period": {int(float(atr_period))},
    "_atr2_period": {int(float(atr2_period))},
    "_atr3_period": {int(float(atr3_period))},
    "_atr4_period": {int(float(atr4_period))},
    "_highest_period": {int(float(highest_period))},
    "_lowest_period": {int(float(lowest_period))},
    "_highest_price_mode": {int(highest_price_mode)},
    "_lowest_price_mode": {int(lowest_price_mode)},
    "_lots": {float(lots)},
    "_stop_loss_coef": {float(stop_loss_coef)},
    "_take_profit_coef": {float(take_profit_coef)},
    "_stop_loss_coef_2": {float(_find_param(params, "stoplosscoef2", default=stop_loss_coef))},
    "_take_profit_coef_2": {float(_find_param(params, "profittargetcoef2", default=take_profit_coef))},
    "_trailing_stop_1": {float(trailing_stop_1)},
    "_trailing_activation_coef": {float(trailing_activation_coef)},
    "_trailing_stop_coef_1": {float(trailing_stop_coef_1)},
}})
'''
    return src, warnings
