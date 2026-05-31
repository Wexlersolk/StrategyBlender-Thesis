from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload, direction_mode as _direction_mode, canonical_symbol as _canonical_symbol

@register_template(
    name="hk50_test_market",
    description="Test template for HK50 engine verification.",
    family="hk50_test",
    regime="Test",
    supported_symbols=("HK50.cash",),
    supported_timeframes=("H4",),
    preferred_timeframes=("H4",),
    sort_order=99
)
def build_hk50_test_market_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol")
    timeframe = _required(payload, "timeframe")
    
    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params={"mmLots": 1.0, "SL_points": 1000.0, "TP_points": 1000.0},
        min_bars=10,
        lot_value=0.1285,
        indicators=[],
        series=[
            SeriesSpec("long_signal", 'pd.Series(True, index=df.index)'),
        ],
        entries=[
            EntryRuleSpec(
                name="test_long",
                side="long",
                order_type="market",
                when='True',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open - float(self.p("SL_points"))',
                take_profit='ctx.open + float(self.p("TP_points"))',
                comment="test_long",
            ),
        ],
    )
