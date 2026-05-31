from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="sqx_hk50_after_retest_h4",
    description="Native HK50 H4 after-retest family using ADX, SAR, and Ichimoku.",
    family="index_retest_breakout",
    regime="Retest then continuation breakout",
    supported_symbols=("HK50.cash", "GER40.cash", "US30.cash"),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=80
)
def build_hk50_after_retest_h4_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    defaults = {
        "DIPeriod1": 14,
        "SARStep": 0.266,
        "SARMax": 0.69,
        "ATRPeriod1": 20,
        "PriceEntryMult1": 0.3,
        "StopLossATR": 2.0,
        "ProfitTargetATR": 3.0,
        "mmLots": 1.0,
        "SignalTimeRangeFrom": "00:13",
        "SignalTimeRangeTo": "00:26",
    }
    for key, value in defaults.items():
        params.setdefault(key, value)
    trend_bias_mode = str(payload.get("trend_bias_mode", "sar_bias"))
    entry_style = str(payload.get("entry_style", "stop"))
    if trend_bias_mode == "ichimoku_bias":
        long_signal = '(df["close"] > df["ichi_kijun"]) & (df["adx_plus"] > df["adx_minus"])'
        short_signal = '(df["close"] < df["ichi_kijun"]) & (df["adx_minus"] > df["adx_plus"])'
    elif trend_bias_mode == "adx_bias":
        long_signal = '_rising(df["adx_plus"], 2, 2) & (df["adx_plus"] > df["adx_minus"])'
        short_signal = '_rising(df["adx_minus"], 2, 2) & (df["adx_minus"] > df["adx_plus"])'
    else:
        long_signal = '_rising(df["adx_plus"], 2, 3) & (df["adx_plus"] > df["adx_minus"]) & (df["close"] > df["sar"])'
        short_signal = '_rising(df["adx_minus"], 2, 3) & (df["adx_minus"] > df["adx_plus"]) & (df["close"] < df["sar"])'
    long_order_type = "market" if entry_style == "market_reclaim" else "buy_stop"
    short_order_type = "market" if entry_style == "market_reclaim" else "sell_stop"
    long_price = None if long_order_type == "market" else 'float(df["ichi_kijun"].iloc[i - 3]) + float(self.p("PriceEntryMult1")) * float(df["atr"].iloc[i - 3])'
    short_price = None if short_order_type == "market" else 'float(df["ichi_kijun"].iloc[i - 3]) - float(self.p("PriceEntryMult1")) * float(df["atr"].iloc[i - 3])'
    long_entry_base = "ctx.open" if long_order_type == "market" else f"({long_price})"
    short_entry_base = "ctx.open" if short_order_type == "market" else f"({short_price})"
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 40)),
        lot_value=float(payload.get("lot_value", 0.1285)),
        description=payload.get("description", "HK50 H4 AfterRetest family using ADX, Ichimoku, and SAR."),
        indicators=[
            IndicatorSpec("adx", "sq_adx", {"high": "high", "low": "low", "close": "close", "period": {"param": "DIPeriod1"}}, outputs={"plus_di": "adx_plus", "minus_di": "adx_minus"}),
            IndicatorSpec("sar", "sq_parabolic_sar", {"high": "high", "low": "low", "step": {"param": "SARStep"}, "maximum": {"param": "SARMax"}}),
            IndicatorSpec("ichi", "sq_ichimoku", {"high": "high", "low": "low", "close": "close", "tenkan": 9, "kijun": 26, "senkou": 51}, outputs={"kijun": "ichi_kijun"}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod1"}}),
        ],
        series=[
            SeriesSpec("long_signal", long_signal),
            SeriesSpec("short_signal", short_signal),
        ],
        exits=[
            ExitRuleSpec("session_exit", 'ctx.has_position and not _in_time_window(ctx.time, str(self.p("SignalTimeRangeFrom")), str(self.p("SignalTimeRangeTo")))'),
        ],
        entries=[
            EntryRuleSpec(
                name="hk50_after_long",
                side="long",
                order_type=long_order_type,
                when='bool(df["long_signal"].iloc[i])',
                price=long_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{long_entry_base} - float(self.p("StopLossATR")) * float(df["atr"].iloc[i - 1])',
                take_profit=f'{long_entry_base} + float(self.p("ProfitTargetATR")) * float(df["atr"].iloc[i - 1])',
                comment="hk50_after_long",
                expiry_bars=8,
            ),
            EntryRuleSpec(
                name="hk50_after_short",
                side="short",
                order_type=short_order_type,
                when='bool(df["short_signal"].iloc[i])',
                price=short_price,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{short_entry_base} + float(self.p("StopLossATR")) * float(df["atr"].iloc[i - 1])',
                take_profit=f'{short_entry_base} - float(self.p("ProfitTargetATR")) * float(df["atr"].iloc[i - 1])',
                comment="hk50_after_short",
                expiry_bars=8,
            ),
        ],
    )
