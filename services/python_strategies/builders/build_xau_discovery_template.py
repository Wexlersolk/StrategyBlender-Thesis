from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="xau_discovery_grammar",
    description="Generic discovery grammar family with genetic discovery blocks.",
    family="market_discovery",
    regime="Genetic market discovery",
    supported_symbols=(),
    supported_timeframes=("M15", "M30", "H1", "H4"),
    preferred_timeframes=("M15", "M30", "H1", "H4"),
    sort_order=35
)
def build_xau_discovery_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    normalized_symbol = _canonical_symbol(symbol)
    is_xau = normalized_symbol == "XAUUSD"
    
    defaults = {
        "HighestPeriod": 24,
        "LowestPeriod": 24,
        "ATRPeriod": 14,
        "FastEMA": 21,
        "SlowEMA": 55,
        "RSIPeriod": 14,
        "BBWRPeriod": 24,
        "BBWRMin": 0.1,
        "EntryBufferATR": 0.15,
        "StopLossATR": 1.4,
        "ProfitTargetATR": 2.8,
        "TrailATR": 1.1,
        "ExitAfterBars": 18,
        "PullbackLookback": 5,
        "PullbackATR": 0.6,
        "ReclaimATR": 0.4,
        "BreakEvenATR": 0.8,
        "TimeStopATR": 0.4,
        "MaxDistancePct": 3.5,
        "mmLots": 1.0,
        "ChopPeriod": 14,
        "ChopThreshold": 55.0,
        "VWAPPeriod": 24,
        "QQERSIPeriod": 14,
        "QQESmoothPeriod": 5,
        "QQEFactor": 4.236,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)

    entry_archetype = str(payload.get("entry_archetype", "breakout_stop"))
    volatility_filter = str(payload.get("volatility_filter", "bb_width"))
    session_filter = str(payload.get("session_filter", "london_ny"))
    stop_model = str(payload.get("stop_model", "atr"))
    target_model = str(payload.get("target_model", "fixed_rr"))
    exit_model = str(payload.get("exit_model", "session_close"))
    direction_mode = _direction_mode(payload)

    session_windows = {
        "all_day": ("00:00", "23:59"),
        "london_only": ("06:00", "11:59"),
        "ny_only": ("12:00", "18:00"),
        "london_ny": ("06:00", "18:00"),
    }
    session_from, session_to = session_windows.get(session_filter, ("06:00", "18:00"))
    params.setdefault("SignalTimeRangeFrom", session_from)
    params.setdefault("SignalTimeRangeTo", session_to)

    if volatility_filter == "none":
        volatility_ok = "True"
    elif volatility_filter == "atr_expansion":
        volatility_ok = 'df["atr"].shift(1) >= (df["atr"].shift(1).rolling(48, min_periods=12).mean() * 1.05)'
    elif volatility_filter == "session_impulse":
        volatility_ok = 'abs(df["close"].shift(1) - df["open"].shift(1)) >= (df["atr"].shift(1) * 0.75)'
    elif volatility_filter == "choppiness_filter":
        volatility_ok = 'df["chop"].shift(1) < float(self.p("ChopThreshold"))'
    else:
        volatility_ok = 'df["bbwr"].shift(1) >= float(self.p("BBWRMin"))'

    if entry_archetype == "ema_reclaim":
        long_signal = (
            '(df["close"].shift(1) > df["ema_slow"].shift(1)) & '
            '(df["low"].shift(1).rolling(int(self.p("PullbackLookback")), min_periods=2).min() < df["ema_fast"].shift(1)) & '
            '(df["close"].shift(1) > df["ema_fast"].shift(1)) & '
            '(df["close"].shift(2) <= df["ema_fast"].shift(2))'
        )
        short_signal = (
            '(df["close"].shift(1) < df["ema_slow"].shift(1)) & '
            '(df["high"].shift(1).rolling(int(self.p("PullbackLookback")), min_periods=2).max() > df["ema_fast"].shift(1)) & '
            '(df["close"].shift(1) < df["ema_fast"].shift(1)) & '
            '(df["close"].shift(2) >= df["ema_fast"].shift(2))'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "heiken_reclaim":
        long_signal = (
            '(df["close"].shift(1) > df["ema_slow"].shift(1)) & '
            '(df["ha_close"].shift(1) > df["ha_open"].shift(1)) & '
            '(df["ha_close"].shift(2) <= df["ha_open"].shift(2))'
        )
        short_signal = (
            '(df["close"].shift(1) < df["ema_slow"].shift(1)) & '
            '(df["ha_close"].shift(1) < df["ha_open"].shift(1)) & '
            '(df["ha_close"].shift(2) >= df["ha_open"].shift(2))'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "ichimoku_momentum":
        long_signal = (
            '(df["tenkan"].shift(1) > df["kijun"].shift(1)) & '
            '(df["close"].shift(1) > df["kijun"].shift(1)) & '
            '(df["tenkan"].shift(2) <= df["kijun"].shift(2))'
        )
        short_signal = (
            '(df["tenkan"].shift(1) < df["kijun"].shift(1)) & '
            '(df["close"].shift(1) < df["kijun"].shift(1)) & '
            '(df["tenkan"].shift(2) >= df["kijun"].shift(2))'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "atr_pullback_limit":
        long_signal = '(df["close"].shift(1) > df["ema_slow"].shift(1)) & (df["close"].shift(1) > df["ema_fast"].shift(1))'
        short_signal = '(df["close"].shift(1) < df["ema_slow"].shift(1)) & (df["close"].shift(1) < df["ema_fast"].shift(1))'
        long_order_type = "buy_limit"
        short_order_type = "sell_limit"
        long_price = 'float(df["ema_fast"].iloc[i-1]) - (float(df["atr"].iloc[i-1]) * float(self.p("PullbackATR")))'
        short_price = 'float(df["ema_fast"].iloc[i-1]) + (float(df["atr"].iloc[i-1]) * float(self.p("PullbackATR")))'
        long_entry_base = f"({long_price})"
        short_entry_base = f"({short_price})"
    elif entry_archetype == "pullback_trend":
        long_signal = (
            '(df["close"].shift(1) > df["ema_slow"].shift(1)) & '
            '(df["low"].shift(1).rolling(int(self.p("PullbackLookback")), min_periods=2).min() <= df["ema_fast"].shift(1)) & '
            '(df["close"].shift(1) > df["ema_fast"].shift(1))'
        )
        short_signal = (
            '(df["close"].shift(1) < df["ema_slow"].shift(1)) & '
            '(df["high"].shift(1).rolling(int(self.p("PullbackLookback")), min_periods=2).max() >= df["ema_fast"].shift(1)) & '
            '(df["close"].shift(1) < df["ema_fast"].shift(1))'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "session_reclaim":
        long_signal = (
            '(df["low"].shift(1) < df["lowest_level"].shift(1)) & '
            '(df["close"].shift(1) > df["ema_fast"].shift(1)) & '
            '(df["rsi"].shift(1) > 50.0)'
        )
        short_signal = (
            '(df["high"].shift(1) > df["highest_level"].shift(1)) & '
            '(df["close"].shift(1) < df["ema_fast"].shift(1)) & '
            '(df["rsi"].shift(1) < 50.0)'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "range_fade_reclaim":
        long_signal = (
            '(df["close"].shift(1) > df["open"].shift(1)) & '
            '(df["close"].shift(1) > (df["lowest_level"].shift(1) + float(self.p("ReclaimATR")) * df["atr"].shift(1))) & '
            '(df["rsi"].shift(1) < 45.0)'
        )
        short_signal = (
            '(df["close"].shift(1) < df["open"].shift(1)) & '
            '(df["close"].shift(1) < (df["highest_level"].shift(1) - float(self.p("ReclaimATR")) * df["atr"].shift(1))) & '
            '(df["rsi"].shift(1) > 55.0)'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "breakout_close":
        long_signal = 'df["close"] > df["highest_level"].shift(1)'
        short_signal = 'df["close"] < df["lowest_level"].shift(1)'
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "breakout_stop":
        # breakout_stop: Anticipatory Pending Stop
        long_signal = 'df["close"].shift(1) <= df["highest_level"].shift(1)'
        short_signal = 'df["close"].shift(1) >= df["lowest_level"].shift(1)'
        long_order_type = "buy_stop"
        short_order_type = "sell_stop"
        long_price = 'float(df["highest_level"].iloc[i-1]) + (float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR")))'
        short_price = 'float(df["lowest_level"].iloc[i-1]) - (float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR")))'
        long_entry_base = f"({long_price})"
        short_entry_base = f"({short_price})"
    elif entry_archetype == "vwap_pullback":
        long_signal = (
            '(df["close"].shift(1) > df["vwap"].shift(1)) & '
            '(df["low"].shift(1) <= df["vwap"].shift(1) + df["atr"].shift(1) * float(self.p("PullbackATR"))) & '
            '(df["close"].shift(1) > df["ema_fast"].shift(1))'
        )
        short_signal = (
            '(df["close"].shift(1) < df["vwap"].shift(1)) & '
            '(df["high"].shift(1) >= df["vwap"].shift(1) - df["atr"].shift(1) * float(self.p("PullbackATR"))) & '
            '(df["close"].shift(1) < df["ema_fast"].shift(1))'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    elif entry_archetype == "qqe_momentum":
        long_signal = (
            '(df["qqe_main"].shift(1) > 50.0) & '
            '(df["qqe_main"].shift(2) <= 50.0)'
        )
        short_signal = (
            '(df["qqe_main"].shift(1) < 50.0) & '
            '(df["qqe_main"].shift(2) >= 50.0)'
        )
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    else:
        # Default fallback to avoid UnboundLocalError
        long_signal = "df['close'] > 1e9" # Impossible signal
        short_signal = "df['close'] > 1e9"
        long_order_type = "market"
        short_order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"

    if stop_model == "channel":
        long_stop = 'min(float(df["lowest_level"].iloc[i-1]), float(ctx.open) - float(df["atr"].iloc[i-1]) * 0.5)'
        short_stop = 'max(float(df["highest_level"].iloc[i-1]), float(ctx.open) + float(df["atr"].iloc[i-1]) * 0.5)'
    elif stop_model == "swing":
        long_stop = 'float(df["low"].shift(1).rolling(int(self.p("PullbackLookback")) + 2, min_periods=2).min().iloc[i])'
        short_stop = 'float(df["high"].shift(1).rolling(int(self.p("PullbackLookback")) + 2, min_periods=2).max().iloc[i])'
    elif stop_model == "atr_anchor":
        long_stop = 'min(float(df["ema_fast"].iloc[i-1]), float(df["lowest_level"].iloc[i-1])) - (float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR")) * 0.6)'
        short_stop = 'max(float(df["ema_fast"].iloc[i-1]), float(df["highest_level"].iloc[i-1])) + (float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR")) * 0.6)'
    else:
        long_stop = f"{long_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('StopLossATR')))"
        short_stop = f"{short_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('StopLossATR')))"

    if target_model == "trend_runner":
        long_target = f"{long_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.6)"
        short_target = f"{short_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.6)"
    elif target_model == "atr_scaled":
        long_target = f"{long_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.2)"
        short_target = f"{short_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.2)"
    elif target_model == "asymmetric_runner":
        long_target = f"{long_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.9)"
        short_target = f"{short_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')) * 1.4)"
    else:
        long_target = f"{long_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')))"
        short_target = f"{short_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')))"

    exit_after_bars = 'int(self.p("ExitAfterBars"))' if exit_model in {"time_exit", "atr_time_stop"} else None
    trail_dist = 'float(df["atr"].iloc[i-1]) * float(self.p("TrailATR"))' if exit_model in {"trailing_atr", "break_even_then_trail"} else None
    trail_activation = 'float(df["atr"].iloc[i-1])' if exit_model == "trailing_atr" else 'float(df["atr"].iloc[i-1]) * float(self.p("BreakEvenATR"))' if exit_model == "break_even_then_trail" else None

    exits: list[ExitRuleSpec] = []
    if session_filter != "all_day" or exit_model == "session_close":
        exits.append(
            ExitRuleSpec(
                "session_exit",
                'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))',
            )
        )
    if exit_model == "channel_flip":
        exits.extend(
            [
                ExitRuleSpec("channel_flip_long", 'ctx.has_long and bool(df["close"].iloc[i-1] < df["ema_fast"].iloc[i-1])'),
                ExitRuleSpec("channel_flip_short", 'ctx.has_short and bool(df["close"].iloc[i-1] > df["ema_fast"].iloc[i-1])'),
            ]
        )
    if exit_model == "atr_time_stop":
        exits.extend(
            [
                ExitRuleSpec("atr_time_stop_long", 'ctx.has_long and (ctx.long_entry_price - ctx.open) > float(df["atr"].iloc[i-1]) * float(self.p("TimeStopATR"))'),
                ExitRuleSpec("atr_time_stop_short", 'ctx.has_short and (ctx.open - ctx.short_entry_price) > float(df["atr"].iloc[i-1]) * float(self.p("TimeStopATR"))'),
            ]
        )
    if exit_model == "trailing_swing":
        exits.extend(
            [
                ExitRuleSpec("trailing_swing_long", 'ctx.has_long and df["close"].iloc[i-1] < df["lowest_level"].iloc[i-1]'),
                ExitRuleSpec("trailing_swing_short", 'ctx.has_short and df["close"].iloc[i-1] > df["highest_level"].iloc[i-1]'),
            ]
        )
    if exit_model == "friday_flat":
        exits.append(
            ExitRuleSpec("friday_flat", 'ctx.has_position and ctx.time.weekday() == 4 and ctx.time.hour >= 20')
        )
    if exit_model == "ema_flip":
        exits.extend(
            [
                ExitRuleSpec("ema_flip_long", 'ctx.has_long and bool(df["close"].iloc[i-1] < df["ema_fast"].iloc[i-1])'),
                ExitRuleSpec("ema_flip_short", 'ctx.has_short and bool(df["close"].iloc[i-1] > df["ema_fast"].iloc[i-1])'),
            ]
        )

    entry_gate = '_in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'
    # Market-entry families must only consume closed-bar state; otherwise the native engine
    # can implicitly use the same bar's close/low/high while still entering at that bar's open.
    long_signal_ref = 'bool(df["long_signal"].eq(True).iloc[i])'
    short_signal_ref = 'bool(df["short_signal"].eq(True).iloc[i])'
    volatility_ref = 'bool(df["volatility_ok"].eq(True).iloc[i])'
    distance_price_ref = 'float(df["close"].iloc[i-1])'
    distance_gate = f'(abs(float(ctx.open) - {distance_price_ref}) / max(float(ctx.open), 1e-9) * 100.0 <= float(self.p("MaxDistancePct")))'


    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="xau_discovery_long",
                side="long",
                order_type=long_order_type,
                when=f'{volatility_ref} and {entry_gate} and {long_signal_ref} and {distance_gate}',
                price=long_price,
                lots='float(self.p("mmLots"))',
                stop_loss=long_stop,
                take_profit=long_target,
                trail_dist=trail_dist,
                trail_activation=trail_activation,
                exit_after_bars=exit_after_bars,
                expiry_bars=3 if long_order_type != "market" else 1,
                comment="xau_discovery_long",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="xau_discovery_short",
                side="short",
                order_type=short_order_type,
                when=f'{volatility_ref} and {entry_gate} and {short_signal_ref} and {distance_gate}',
                price=short_price,
                lots='float(self.p("mmLots"))',
                stop_loss=short_stop,
                take_profit=short_target,
                trail_dist=trail_dist,
                trail_activation=trail_activation,
                exit_after_bars=exit_after_bars,
                expiry_bars=3 if short_order_type != "market" else 1,
                comment="xau_discovery_short",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 40)),
        lot_value=float(payload.get("lot_value", 100.0 if is_xau else 1.0)),
        description=payload.get("description", "Constrained XAU discovery template with mixable approved blocks."),
        indicators=[
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 2}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 3}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
            IndicatorSpec("bbwr", "sq_bb_width_ratio", {"series": "close", "period": {"param": "BBWRPeriod"}, "deviations": 2.0}),
            IndicatorSpec("ema_fast", "ema", {"series": "close", "period": {"param": "FastEMA"}}),
            IndicatorSpec("ema_slow", "ema", {"series": "close", "period": {"param": "SlowEMA"}}),
            IndicatorSpec("ha", "sq_heiken_ashi", {"df": "df"}, outputs={"open": "ha_open", "high": "ha_high", "low": "ha_low", "close": "ha_close"}),
            IndicatorSpec("ichi", "sq_ichimoku", {"high": "high", "low": "low", "close": "close", "tenkan": 9, "kijun": 26, "senkou": 52}, outputs={"tenkan": "tenkan", "kijun": "kijun", "senkou_a": "senkou_a", "senkou_b": "senkou_b"}),
            IndicatorSpec("vwap", "sq_vwap", {"open_": "open", "high": "high", "low": "low", "close": "close", "volume": "volume", "period": {"param": "VWAPPeriod"}}),
            IndicatorSpec("qqe", "sq_qqe", {"close": "close", "rsi_period": {"param": "QQERSIPeriod"}, "smooth_period": {"param": "QQESmoothPeriod"}, "factor": {"param": "QQEFactor"}}, outputs={"qqe": "qqe_main", "upper": "qqe_up", "lower": "qqe_dn"}),
        ],
        series=[
            SeriesSpec("rsi", '100.0 - (100.0 / (1.0 + (df["close"].diff().clip(lower=0).rolling(int(self.p("RSIPeriod")), min_periods=1).mean() / df["close"].diff().clip(upper=0).abs().rolling(int(self.p("RSIPeriod")), min_periods=1).mean().replace(0.0, np.nan)))).fillna(50.0)'),
            SeriesSpec("chop", '100.0 * np.log10(df["atr"].rolling(int(self.p("ChopPeriod"))).sum() / (df["high"].rolling(int(self.p("ChopPeriod"))).max() - df["low"].rolling(int(self.p("ChopPeriod"))).min()).replace(0.0, np.nan)) / np.log10(float(self.p("ChopPeriod")))'),
            SeriesSpec("volatility_ok", volatility_ok),
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        exits=exits,
        entries=entries,
    )
