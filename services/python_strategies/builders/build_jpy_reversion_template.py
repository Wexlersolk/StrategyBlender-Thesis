from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="jpy_reversion",
    description="JPY specific mean reversion using Bollinger Bands and WaveTrend",
    family="mean_reversion",
    regime="Mean reversion",
    sort_order=125
)
def build_jpy_reversion_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")

    bb_period = str(payload.get("bb_period_param", "BBPeriod"))
    bb_dev = str(payload.get("bb_dev_param", "BBDev"))
    wt_channel = str(payload.get("wt_channel_param", "WaveTrendChannel"))
    wt_average = str(payload.get("wt_average_param", "WaveTrendAverage"))
    atr_period = str(payload.get("atr_period_param", "ATRPeriod"))
    lots = str(payload.get("lots_param", "mmLots"))
    stop_loss = str(payload.get("stop_loss_atr_param", "StopLossATR"))
    take_profit = str(payload.get("take_profit_atr_param", "ProfitTargetATR"))
    exit_after = str(payload.get("exit_after_bars_param", "ExitAfterBars"))

    params = dict(payload.get("params", {}))
    params.setdefault(bb_period, 20)
    params.setdefault(bb_dev, 2.5)
    params.setdefault(wt_channel, 10)
    params.setdefault(wt_average, 21)
    params.setdefault(atr_period, 14)
    params.setdefault(lots, 1.0)
    params.setdefault(stop_loss, 2.0)
    params.setdefault(take_profit, 3.0)
    params.setdefault(exit_after, 24)

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=int(payload.get("min_bars", 100)),
        lot_value=float(payload.get("lot_value", 1.0)),
        description=payload.get("description", "JPY mean-reversion template with Bollinger Bands and WaveTrend."),
        indicators=[
            IndicatorSpec(
                "bollinger",
                "bollinger_bands",
                {"open_": "open", "high": "high", "low": "low", "close": "close", "period": _param_payload(params, bb_period), "deviations": _param_payload(params, bb_dev), "mode": 0},
                outputs={"upper": "bb_upper", "lower": "bb_lower", "middle": "bb_middle"},
            ),
            IndicatorSpec(
                "wavetrend",
                "sq_wave_trend",
                {"high": "high", "low": "low", "close": "close", "channel_length": _param_payload(params, wt_channel), "average_length": _param_payload(params, wt_average)},
                outputs={"main": "wt_main", "signal": "wt_signal"},
            ),
            IndicatorSpec("atr", "sq_atr", {"high": "high", "low": "low", "close": "close", "period": _param_payload(params, atr_period)}),
        ],
        series=[
            # Long: Price touched/was below lower band recently + WaveTrend cross up
            SeriesSpec("price_below_lower", 'df["close"] < df["bb_lower"]'),
            SeriesSpec("long_signal", f'(df["price_below_lower"].rolling(3).max().shift(1) > 0) & (df["wt_main"].shift(1) > df["wt_signal"].shift(1)) & (df["wt_main"].shift(2) <= df["wt_signal"].shift(2))'),
            # Short: Price touched/was above upper band recently + WaveTrend cross down
            SeriesSpec("price_above_upper", 'df["close"] > df["bb_upper"]'),
            SeriesSpec("short_signal", f'(df["price_above_upper"].rolling(3).max().shift(1) > 0) & (df["wt_main"].shift(1) < df["wt_signal"].shift(1)) & (df["wt_main"].shift(2) >= df["wt_signal"].shift(2))'),
        ],
        entries=[
            EntryRuleSpec(
                name="long_jpy_reversion",
                side="long",
                order_type="market",
                when='bool(df["long_signal"].iloc[i])',
                lots=f'float(self.p("{lots}"))',
                stop_loss=f'ctx.open - float(df["atr"].iloc[i - 1]) * float(self.p("{stop_loss}"))',
                take_profit=f'ctx.open + float(df["atr"].iloc[i - 1]) * float(self.p("{take_profit}"))',
                comment="template_jpy_reversion_long",
                exit_after_bars=f'int(self.p("{exit_after}"))',
            ),
            EntryRuleSpec(
                name="short_jpy_reversion",
                side="short",
                order_type="market",
                when='bool(df["short_signal"].iloc[i])',
                lots=f'float(self.p("{lots}"))',
                stop_loss=f'ctx.open + float(df["atr"].iloc[i - 1]) * float(self.p("{stop_loss}"))',
                take_profit=f'ctx.open - float(df["atr"].iloc[i - 1]) * float(self.p("{take_profit}"))',
                comment="template_jpy_reversion_short",
                exit_after_bars=f'int(self.p("{exit_after}"))',
            ),
        ],
    )
