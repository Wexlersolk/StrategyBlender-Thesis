from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="us100_ny_momentum_v3",
    description="Alpha-tier NY momentum for NASDAQ. Market entry with EMA pullback and ADX volatility filtering.",
    family="index_momentum",
    regime="Intraday Momentum",
    supported_symbols=("US100.cash", "US30.cash", "US500.cash"),
    supported_timeframes=("M15", "M30", "H1"),
    preferred_timeframes=("M15", "M30", "H1"),
    sort_order=67
)
def build_us100_ny_momentum_v3_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    params = dict(payload.get("params", {}))
    
    defaults = {
        "EMAPeriod": 100,
        "PullbackEMAPeriod": 20,
        "ATRPeriod": 14,
        "ADXPeriod": 14,
        "ADXMin": 20.0,            # Volatility filter
        "StopLossATR": 2.5,
        "ProfitTargetATR": 6.0,
        "TrailingStopATR": 1.5,
        "NYOpenHour": 14, 
        "NYCloseHour": 19,
        "EntryBufferATR": 0.1,
        "mmLots": 1.0,
    }
    for k, v in defaults.items():
        params.setdefault(k, v)

    # V3 logic: Market entry IF:
    # 1. It is the NY Open hour
    # 2. Price is above/below the global trend (EMA 100)
    # 3. Price has recently pulled back to a faster EMA (EMA 20) to filter over-extended moves
    # 4. ADX indicates sufficient trend strength
    
    long_when = (
        'int(ctx.time.hour) == int(self.p("NYOpenHour")) and '
        'float(df["close"].iloc[i-1]) > float(df["ema_trend"].iloc[i-1]) and '
        'float(df["low"].iloc[i-1]) < float(df["ema_pullback"].iloc[i-1]) and '
        'float(df["adx"].iloc[i-1]) > float(self.p("ADXMin"))'
    )
    
    short_when = (
        'int(ctx.time.hour) == int(self.p("NYOpenHour")) and '
        'float(df["close"].iloc[i-1]) < float(df["ema_trend"].iloc[i-1]) and '
        'float(df["high"].iloc[i-1]) > float(df["ema_pullback"].iloc[i-1]) and '
        'float(df["adx"].iloc[i-1]) > float(self.p("ADXMin"))'
    )

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(params["EMAPeriod"]) + 20,
        indicators=[
            IndicatorSpec("ema_trend", "ema", {"series": "close", "period": _param_payload(params, "EMAPeriod")}),
            IndicatorSpec("ema_pullback", "ema", {"series": "close", "period": _param_payload(params, "PullbackEMAPeriod")}),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ATRPeriod")}),
            IndicatorSpec("adx_data", "sq_adx", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, "ADXPeriod")}, outputs={"adx": "adx"}),
        ],
        entries=[
            EntryRuleSpec(
                name="ny_momentum_long_v3",
                side="long",
                order_type="market",
                when=long_when,
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open - float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit='ctx.open + float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_long_v3",
                expiry_bars=1,
            ),
            EntryRuleSpec(
                name="ny_momentum_short_v3",
                side="short",
                order_type="market",
                when=short_when,
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open + float(df["atr"].iloc[i-1]) * float(self.p("StopLossATR"))',
                take_profit='ctx.open - float(df["atr"].iloc[i-1]) * float(self.p("ProfitTargetATR"))',
                trail_dist='float(df["atr"].iloc[i-1]) * float(self.p("TrailingStopATR"))',
                comment="us100_ny_short_v3",
                expiry_bars=1,
            ),
        ],
        exits=[
            ExitRuleSpec("ny_session_close", f'int(ctx.time.hour) >= int(self.p("NYCloseHour"))'),
        ]
    )
