from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_before_retest_h4",
    description="Native HK50 H4 before-retest family using RSI, Fibo, and SMA.",
    family="index_prebreak_setup",
    regime="Pre-break tension before retest",
    supported_symbols=("HK50.cash", "GER40.cash", "US30.cash"),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=90
)
def build_hk50_before_retest_h4_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "RSIPeriod1": 14,
        "Period1": 50,
        "SMAPeriod1": 20,
        "ATRPeriod1": 50,
        "ATRPeriod2": 19,
        "ATRPeriod3": 65,
        "PriceEntryMult1": 0.3,
        "ProfitTargetCoef1": 3.0,
        "TrailingActCef1": 1.4,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:26",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    signal_mode = str(payload.get("signal_mode", "rsi_reversal"))
    entry_style = str(payload.get("entry_style", "stop"))
    if signal_mode == "fibo_reclaim":
        long_signal = '(df["close"] > df["fibo"]) & (df["rsi_1"] < 48.0)'
        short_signal = '(df["close"] < df["fibo"]) & (df["rsi_1"] > 52.0)'
    elif signal_mode == "sma_fade":
        long_signal = '(df["close"] < df["sma_entry"]) & _falling(df["rsi_1"], 2, 1)'
        short_signal = '(df["close"] > df["sma_entry"]) & _rising(df["rsi_1"], 2, 1)'
    else:
        long_signal = '_falling(df["rsi_1"], 2, 1)'
        short_signal = '_rising(df["rsi_1"], 2, 1)'
    long_order_type = "market" if entry_style == "market_reclaim" else "buy_stop"
    short_order_type = "market" if entry_style == "market_reclaim" else "sell_stop"
    long_price = None if long_order_type == "market" else 'float(df["sma_entry"].iloc[i - 3]) + float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i - 1])'
    short_price = None if short_order_type == "market" else 'float(df["sma_entry"].iloc[i - 3]) - float(self.p("PriceEntryMult1")) * float(df["atr_1"].iloc[i - 1])'
    long_entry_base = "ctx.open" if long_order_type == "market" else f"({long_price})"
    short_entry_base = "ctx.open" if short_order_type == "market" else f"({short_price})"
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 70)),
        lot_value=float(payload.get("lot_value", 0.1285)),
        description=payload.get("description", "HK50 H4 BeforeRetest family using RSI, Fibo, SMA, and ATR."),
        indicators=[
            IndicatorSpec("typical_price", "select_price", {"open_": "open", "high": "high", "low": "low", "close": "close", "mode": 5}),
            IndicatorSpec("lowest", "sq_lowest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Period1"}, "mode": 1}),
            IndicatorSpec("highest", "sq_highest", {"open_": "open", "high": "high", "low": "low", "close": "close", "period": {"param": "Period1"}, "mode": 1}),
            IndicatorSpec("fibo", "sq_fibo", {"df": "df", "fibo_range": 2, "x": 0, "fibo_level": -9999999.0, "custom_fibo_level": -61.8, "start_date": None}),
            IndicatorSpec("sma_entry", "sma", {"series": "typical_price", "period": {"param": "SMAPeriod1"}}),
            IndicatorSpec("atr_1", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
            IndicatorSpec("atr_2", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod2"}}),
            IndicatorSpec("atr_3", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod3"}}),
        ],
        series=[
            SeriesSpec("rsi_1", '100.0 - (100.0 / (1.0 + (df["typical_price"].diff().clip(lower=0).rolling(int(self.p("RSIPeriod1")), min_periods=1).mean() / df["typical_price"].diff().clip(upper=0).abs().rolling(int(self.p("RSIPeriod1")), min_periods=1).mean().replace(0.0, np.nan)))).fillna(50.0)'),
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
            SeriesSpec("long_exit_signal", 'df["lowest"].shift(2) != df["fibo"]'),
            SeriesSpec("short_exit_signal", 'df["highest"].shift(2) == df["fibo"]'),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
            ExitRuleSpec("before_retest_long_exit", 'ctx.has_long and bool(df["long_exit_signal"].iloc[i])'),
            ExitRuleSpec("before_retest_short_exit", 'ctx.has_short and bool(df["short_exit_signal"].iloc[i])'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_before_long",
                side="long",
                order_type=long_order_type,
                when='bool(df["long_signal"].iloc[i])',
                price=long_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{long_entry_base} - float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i - 1])',
                take_profit=f'{long_entry_base} + float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr_3"].iloc[i - 1])',
                comment="hk50_before_long",
                expiry_bars=8,
            ),
            EntryRuleSpec(
                name="hk50_before_short",
                side="short",
                order_type=short_order_type,
                when='bool(df["short_signal"].iloc[i])',
                price=short_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{short_entry_base} + float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i - 1])',
                take_profit=f'{short_entry_base} - float(self.p("ProfitTargetCoef1")) * float(df["atr_2"].iloc[i - 1])',
                trail_activation='float(self.p("TrailingActCef1")) * float(df["atr_3"].iloc[i - 1])',
                comment="hk50_before_short",
                expiry_bars=8,
            ),
        ],
    )
