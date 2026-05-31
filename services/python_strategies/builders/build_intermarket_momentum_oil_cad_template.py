from __future__ import annotations
from typing import Any
from ..models import StrategySpec, IndicatorSpec, SeriesSpec, EntryRuleSpec, ExitRuleSpec, register_template
from .utils import required as _required, param_payload as _param_payload

@register_template(
    name="intermarket_momentum_oil_cad",
    description="Correlational momentum between Oil and CAD",
    family="intermarket",
    regime="Trend following",
    sort_order=150
)
def build_intermarket_momentum_oil_cad_template(payload: dict[str, Any]) -> StrategySpec:
    name = _required(payload, "name")
    symbol = _required(payload, "symbol") # Usually USDCAD
    timeframe = _required(payload, "timeframe")

    params = dict(payload.get("params", {}))
    params.setdefault("OilPeriod", 14)
    params.setdefault("MomentumThreshold", 0.0)
    params.setdefault("mmLots", 1.0)
    params.setdefault("StopLossPips", 40.0)
    params.setdefault("ProfitTargetPips", 80.0)

    return StrategySpec(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        params=params,
        min_bars=50,
        series=[
            # This is a conceptual template; actual multi-symbol loading 
            # would happen in the engine/data_loader or via a custom service.
            # Here we simulate the logic assuming 'df' has been joined with Oil data.
            SeriesSpec("oil_momentum", f'df["oil_close"].diff(int(self.p("OilPeriod")))'),
            SeriesSpec("long_signal", f'df["oil_momentum"] < -float(self.p("MomentumThreshold"))'), # Oil down = CAD down = USDCAD up
            SeriesSpec("short_signal", f'df["oil_momentum"] > float(self.p("MomentumThreshold"))'), # Oil up = CAD up = USDCAD down
        ],
        entries=[
            EntryRuleSpec(
                name="buy_usdcad",
                side="long",
                order_type="market",
                when='bool(df["long_signal"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open - float(self.p("StopLossPips")) * ctx.tick_size',
                take_profit='ctx.open + float(self.p("ProfitTargetPips")) * ctx.tick_size',
            ),
            EntryRuleSpec(
                name="sell_usdcad",
                side="short",
                order_type="market",
                when='bool(df["short_signal"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open + float(self.p("StopLossPips")) * ctx.tick_size',
                take_profit='ctx.open - float(df["oil_momentum"].iloc[i]) * 0', # Placeholder
            )
        ]
    )
