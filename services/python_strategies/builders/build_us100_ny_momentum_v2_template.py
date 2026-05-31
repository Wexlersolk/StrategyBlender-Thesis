from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="us100_ny_momentum_v2",
    description="Upgraded NY session momentum for NASDAQ with volatility buffers and flexible entry types.",
    family="index_momentum",
    regime="Intraday Momentum",
    supported_symbols=("US100.cash", "US30.cash", "US500.cash"),
    supported_timeframes=("H1",),
    preferred_timeframes=("H1",),
    sort_order=66
)
def build_us100_ny_momentum_v2_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "EMAPeriod": 200,
        "ATRPeriod": 14,
        "StopLossATR": 2.5,
        "ProfitTargetATR": 6.0,
        "TrailingStopATR": 1.5,
        "NYOpenHour": 13, 
        "NYCloseHour": 20,
        "EntryBufferATR": 0.1,    # Buffer to avoid noise wicks
        "EntryType": "stop",      # 'stop' or 'market'
        "mmLots": 1.0,
    }
    for k, v in defaults.items():
        params.setdefault(k, v)

    entry_type = str(params.get("EntryType", "stop")).lower()
    
    # Logic for Entry Price and "When" condition based on EntryType
    if entry_type == "market":
        # Enter at market if current close > pre_market_high + buffer
        long_price = None
        long_when = 'int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i]) > (float(df["pre_market_high"].iloc[i]) + float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR"))) and float(df["close"].iloc[i-1]) > float(df["ema_trend"].iloc[i-1])'
        order_type_long = "market"
        
        short_price = None
        short_when = 'int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i]) < (float(df["pre_market_low"].iloc[i]) - float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR"))) and float(df["close"].iloc[i-1]) < float(df["ema_trend"].iloc[i-1])'
        order_type_short = "market"
    else:
        # Default to Stop Orders
        long_price = 'float(df["pre_market_high"].iloc[i]) + float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR"))'
        long_when = 'int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i-1]) > float(df["ema_trend"].iloc[i-1])'
        order_type_long = "buy_stop"
        
        short_price = 'float(df["pre_market_low"].iloc[i]) - float(df["atr"].iloc[i-1]) * float(self.p("EntryBufferATR"))'
        short_when = 'int(ctx.time.hour) == int(self.p("NYOpenHour")) and float(df["close"].iloc[i-1]) < float(df["ema_trend"].iloc[i-1])'
        order_type_short = "sell_stop"

    # For stop loss/take profit calculation in market orders, we need a reference price.
    # Since market orders enter at ctx.open (current bar open), we use that.
    sl_price_long = long_price if long_price else 'ctx.open'
    tp_price_long = long_price if long_price else 'ctx.open'
    sl_price_short = short_price if short_price else 'ctx.open'
    tp_price_short = short_price if short_price else 'ctx.open'

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(params["EMAPeriod"]) + 20,
        indicators=[
            IndicatorSpec("ema_trend", "ema", {"series": "close", "period": _param_payload(params, "EMAPeriod")}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ATRPeriod")}),
        ],
        series=[
            SeriesSpec("pre_market_high", 'df["high"].shift(1)'),
            SeriesSpec("pre_market_low", 'df["low"].shift(1)'),
        ],
        entries=[
            EntryRuleSpec(
                name="ny_momentum_long_v2",
                side="long",
                order_type=order_type_long,
                price=long_price,
                when=long_when,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{sl_price_long} - float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit=f'{tp_price_long} + float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_long_v2",
                expiry_bars=1,
            ),
            EntryRuleSpec(
                name="ny_momentum_short_v2",
                side="short",
                order_type=order_type_short,
                price=short_price,
                when=short_when,
                lots='float(self.p("mmLots"))',
                stop_loss=f'{sl_price_short} + float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit=f'{tp_price_short} - float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_short_v2",
                expiry_bars=1,
            ),
        ],
        exits=[
            ExitRuleSpec("ny_session_close", f'int(ctx.time.hour) >= int(self.p("NYCloseHour"))'),
        ]
    )
