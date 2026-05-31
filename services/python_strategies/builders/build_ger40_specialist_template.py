from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="ger40_m15_specialist",
    description="Specialized GER40 M15 template with trend-following breakouts and mean-reversion pullbacks.",
    family="index_specialist",
    regime="High volatility index discovery",
    supported_symbols=("GER40.cash", "GER40", "DE40", "EUREX.FDAX", "US100.cash", "US100", "US500.cash", "US500", "XAUUSD", "XAUUSD.cash", "GOLD"),
    supported_timeframes=("M15", "M30", "H1", "H4"),
    preferred_timeframes=("M15",),
    sort_order=40
)
def build_ger40_specialist_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "HighestPeriod": 16,
        "LowestPeriod": 16,
        "ATRPeriod": 14,
        "FastEMA": 34,
        "SlowEMA": 200,
        "BBWRPeriod": 20,
        "SqueezeThreshold": 0.08,
        "ADXPeriod": 14,
        "ADXMin": 20.0,
        "RSIPeriod": 14,
        "RSILongMin": 50.0,
        "RSIShortMax": 50.0,
        "EntryBufferATR": 0.1,
        "StopLossATR": 3.0,
        "ProfitTargetATR": 6.5,
        "TrailATR": 1.5,
        "BreakEvenATR": 1.2,
        "PullbackATR": 0.7,
        "MinATR": 0.0,
        "mmLots": 1.0,
        "MaxDistancePct": 2.5,
    }
    for key, value in defaults.items():
        params.setdefault(key, value)

    # Strategy Configuration
    archetype = str(payload.get("archetype", "trend_breakout"))
    session_filter = str(payload.get("session_filter", "london_ny"))
    direction_mode = _direction_mode(payload)
    
    session_windows = {
        "london_morning": ("07:00", "10:00"),
        "london_only": ("07:00", "11:00"),
        "ny_only": ("13:30", "17:30"),
        "london_ny": ("07:00", "17:30"),
        "all_day": ("00:00", "23:59"),
    }
    session_from, session_to = session_windows.get(session_filter, ("07:00", "16:00"))
    params.setdefault("SignalTimeRangeFrom", session_from)
    params.setdefault("SignalTimeRangeTo", session_to)

    # Global Filters (Series-based)
    trend_filter_long = '(df["close"] > df["ema_slow"])'
    trend_filter_short = '(df["close"] < df["ema_slow"])'
    
    # New filters: ADX for trend strength, RSI for momentum
    trend_strength = '(df["adx"] > float(self.p("ADXMin")))'
    momentum_long = '(df["rsi"] > float(self.p("RSILongMin")))'
    momentum_short = '(df["rsi"] < float(self.p("RSIShortMax")))'
    
    # Squeeze: Volatility expansion (current width > rolling average width)
    squeeze_ok = '(df["bbwr"] > df["bbwr"].rolling(50).mean())'
    
    # Volatility floor
    vol_floor = '(df["atr"] > float(self.p("MinATR")))'

    common_long = f'({trend_filter_long} & {trend_strength} & {momentum_long} & {squeeze_ok} & {vol_floor})'
    common_short = f'({trend_filter_short} & {trend_strength} & {momentum_short} & {squeeze_ok} & {vol_floor})'

    if archetype == "trend_breakout":
        # Enter on break of recent high/low
        long_signal_expr = f'({common_long} & (df["close"] <= df["highest_level"]))'
        short_signal_expr = f'({common_short} & (df["close"] >= df["lowest_level"]))'
        order_type = "stop" # buy_stop / sell_stop
        # Prices use iloc[i-1] because they are evaluated at bar i for an order at bar i
        long_price = 'float(df["highest_level"].iloc[i-1]) + (float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR")))'
        short_price = 'float(df["lowest_level"].iloc[i-1]) - (float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR")))'
        long_entry_base = f"({long_price})"
        short_entry_base = f"({short_price})"
    
    elif archetype == "ema_pullback":
        # Mean reversion: Enter on pullback to Fast EMA in trend direction
        long_signal_expr = f'({common_long} & (df["low"].rolling(5).min() <= df["ema_fast"]) & (df["close"] > df["ema_fast"]))'
        short_signal_expr = f'({common_short} & (df["high"].rolling(5).max() >= df["ema_fast"]) & (df["close"] < df["ema_fast"]))'
        order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"
    
    else: # Default/Session Reclaim
        long_signal_expr = f'({common_long} & (df["low"] < df["lowest_level"]) & (df["close"] > df["ema_fast"]))'
        short_signal_expr = f'({common_short} & (df["high"] > df["highest_level"]) & (df["close"] < df["ema_fast"]))'
        order_type = "market"
        long_price = None
        short_price = None
        long_entry_base = "ctx.open"
        short_entry_base = "ctx.open"

    # Stop Loss & Take Profit
    long_stop = f"{long_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('StopLossATR')))"
    short_stop = f"{short_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('StopLossATR')))"
    
    long_target = f"{long_entry_base} + (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')))"
    short_target = f"{short_entry_base} - (float(df['atr'].iloc[i-1]) * float(self.p('ProfitTargetATR')))"

    entry_gate = '_in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'
    
    # We use SeriesSpec to pre-calculate the signal for all bars, shifted by 1 to represent "previous bar signal"
    series = [
        SeriesSpec("long_signal", f"({long_signal_expr}).shift(1)"),
        SeriesSpec("short_signal", f"({short_signal_expr}).shift(1)"),
    ]

    entries: list[EntryRuleSpec] = []
    if direction_mode != "short_only":
        entries.append(
            EntryRuleSpec(
                name="ger_long",
                side="long",
                order_type="buy_stop" if order_type == "stop" else "market",
                when=f'{entry_gate} and bool(df["long_signal"].iloc[i])',
                price=long_price,
                lots='float(self.p("mmLots"))',
                stop_loss=long_stop,
                take_profit=long_target,
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailATR"))',
                trail_activation='float(df["atr"].iloc[i-1]) * float(self.p("BreakEvenATR"))',
                expiry_bars=8,
                comment=f"ger_long_{archetype}",
            )
        )
    if direction_mode != "long_only":
        entries.append(
            EntryRuleSpec(
                name="ger_short",
                side="short",
                order_type="sell_stop" if order_type == "stop" else "market",
                when=f'{entry_gate} and bool(df["short_signal"].iloc[i])',
                price=short_price,
                lots='float(self.p("mmLots"))',
                stop_loss=short_stop,
                take_profit=short_target,
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailATR"))',
                trail_activation='float(df["atr"].iloc[i-1]) * float(self.p("BreakEvenATR"))',
                expiry_bars=8,
                comment=f"ger_short_{archetype}",
            )
        )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=200,
        lot_value=1.0,
        description=f"GER40 Specialist [{archetype}] with trend and volatility filters.",
        indicators=[
            IndicatorSpec("highest_level", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "HighestPeriod"}, "mode": 2}),
            IndicatorSpec("lowest_level", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "LowestPeriod"}, "mode": 3}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}}),
            IndicatorSpec("bbwr", "sq_bb_width_ratio", {"series": "close", "period": {"param": "BBWRPeriod"}, "deviations": 2.0}),
            IndicatorSpec("adx_data", "sq_adx", {"high": "high", "low": "low", "close": "close", "period": {"param": "ADXPeriod"}}, outputs={"adx": "adx"}),
            IndicatorSpec("rsi", "rsi", {"series": "close", "period": {"param": "RSIPeriod"}}),
            IndicatorSpec("ema_fast", "ema", {"series": "close", "period": {"param": "FastEMA"}}),
            IndicatorSpec("ema_slow", "ema", {"series": "close", "period": {"param": "SlowEMA"}}),
        ],

        series=series,
        exits=[
            ExitRuleSpec("friday_exit", "ctx.has_position and ctx.time.weekday() == 4 and ctx.time.hour >= 20"),
            ExitRuleSpec("session_end", 'ctx.has_position and not _in_time_window(ctx.time, "01:00", "20:00")'),
        ],
        entries=entries,
    )
