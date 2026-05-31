from __future__ import annotations

from typing import Any
from .models import (
    IndicatorSpec, StrategySpec, SUPPORTED_INDICATORS, SERIES_ARG_RENDERERS
)
from .validator import validate_expression
from .utils import class_name_from_slug

def normalize_indicator_kind(kind: str) -> str:
    if kind not in SUPPORTED_INDICATORS:
        supported = ", ".join(sorted(SUPPORTED_INDICATORS))
        raise ValueError(f"Unsupported indicator kind: {kind}. Supported values: {supported}")
    return SUPPORTED_INDICATORS[kind]

def render_code_value(value: Any) -> str:
    if isinstance(value, dict) and set(value) == {"param"}:
        return f"self.p({value['param']!r})"
    if isinstance(value, str):
        return repr(value)
    return repr(value)

def render_indicator_arg(arg_name: str, value: Any) -> str:
    if isinstance(value, dict) and "param" in value:
        p = f"self.p({value['param']!r})"
        if "multiplier" in value:
            p = f"int({p} * {value['multiplier']})"
        return p
    if arg_name in SERIES_ARG_RENDERERS:
        if not isinstance(value, str):
            raise ValueError(f"Indicator argument {arg_name} must reference a dataframe column name")
        return SERIES_ARG_RENDERERS[arg_name](value)
    return render_code_value(value)

import inspect
from engine.indicators import INDICATOR_REGISTRY

def render_indicator(spec: IndicatorSpec) -> tuple[list[str], str]:
    func_name = normalize_indicator_kind(spec.kind)
    
    if func_name == "ema":
        args = f"{render_indicator_arg('series', spec.args.get('series', 'close'))}, {render_indicator_arg('period', spec.args.get('period'))}"
    elif func_name in ("sma", "wma", "smma"):
        args = f"{render_indicator_arg('series', spec.args.get('series', 'close'))}, {render_indicator_arg('period', spec.args.get('period'))}"
    elif func_name == "sq_atr":
        args = f"{render_indicator_arg('high', spec.args.get('high', 'high'))}, {render_indicator_arg('low', spec.args.get('low', 'low'))}, {render_indicator_arg('close', spec.args.get('close', 'close'))}, {render_indicator_arg('period', spec.args.get('period'))}"
    elif func_name == "rsi":
        args = f"{render_indicator_arg('series', spec.args.get('series', 'close'))}, {render_indicator_arg('period', spec.args.get('period'))}"
    elif func_name == "sq_ichimoku":
        args = f"{render_indicator_arg('high', spec.args.get('high', 'high'))}, {render_indicator_arg('low', spec.args.get('low', 'low'))}, {render_indicator_arg('close', spec.args.get('close', 'close'))}, {render_indicator_arg('tenkan', spec.args.get('tenkan'))}, {render_indicator_arg('kijun', spec.args.get('kijun'))}, {render_indicator_arg('senkou', spec.args.get('senkou'))}"
    else:
        func = next((v for k, v in INDICATOR_REGISTRY.items() if getattr(v, '__name__', '') == func_name), None)
        if func:
            sig = inspect.signature(func)
            arg_names = list(sig.parameters.keys())
            ordered_args = []
            for arg_name in arg_names:
                if arg_name in spec.args:
                    ordered_args.append(render_indicator_arg(arg_name, spec.args[arg_name]))
                elif arg_name == 'open_':
                    ordered_args.append(render_indicator_arg(arg_name, spec.args.get('open_', 'open')))
                elif arg_name in ['high', 'low', 'close', 'volume', 'series', 'df']:
                    ordered_args.append(render_indicator_arg(arg_name, spec.args.get(arg_name, arg_name)))
            args = ", ".join(ordered_args)
        else:
            args = ", ".join(
                render_indicator_arg(arg_name, arg_value)
                for arg_name, arg_value in spec.args.items()
            )

    lines: list[str] = []
    if spec.outputs:
        temp_name = f"_{spec.name}_result"
        lines.append(f"        {temp_name} = {func_name}({args})")
        for source_key, column_name in spec.outputs.items():
            lines.append(f'        df[{column_name!r}] = {temp_name}[{source_key!r}]')
    else:
        lines.append(f'        df[{spec.name!r}] = {func_name}({args})')

    return lines, func_name

def render_optional_numeric(value: int | str | None) -> str:
    if value is None:
        return "0"
    if isinstance(value, int):
        return str(value)
    validate_expression(value)
    return value

from dataclasses import asdict

def serialize_spec(spec: StrategySpec) -> dict[str, Any]:
    return asdict(spec)


def render_strategy_code(spec: StrategySpec, strategy_slug: str) -> str:
    class_name = class_name_from_slug(strategy_slug)
    
    lines = [
        "from __future__ import annotations",
        "import pandas as pd",
        "import numpy as np",
        "from engine.base_strategy import BaseStrategy",
        "from engine.indicators import *",
        "from engine.policy import *",
        "",
        f"class {class_name}(BaseStrategy):",
        "    \"\"\"",
        f"    {spec.description or 'Generated Strategy'}",
        "    \"\"\"",
        "",
        "    def __init__(self, **kwargs):",
        "        super().__init__(**kwargs)",
    ]
    
    # Parameters
    lines.append(f"    params = {spec.params!r}")
    lines.append("")
    
    # Indicators
    lines.append("    def compute_indicators(self, df: pd.DataFrame):")
    if not spec.indicators and not spec.series:
        lines.append("        pass")
    else:
        for ind in spec.indicators:
            ind_lines, _ = render_indicator(ind)
            lines.extend(ind_lines)
        for ser in spec.series:
            validate_expression(ser.expression)
            lines.append(f"        df[{ser.name!r}] = {ser.expression}")
    lines.append("")
    
    # on_bar logic
    lines.append("    def on_bar(self, ctx, i: int):")
    if not spec.entries:
        lines.append("        pass")
    else:
        # Simple rendering for now, can be more complex if needed
        for entry in spec.entries:
            validate_expression(entry.when)
            lines.append(f"        if {entry.when}:")
            lines.append(f"            self.{entry.side}({entry.lots}, stop_loss={entry.stop_loss}, take_profit={entry.take_profit})")
            
    # Exit logic
    for exit_rule in spec.exits:
        validate_expression(exit_rule.when)
        lines.append(f"        if {exit_rule.when}:")
        lines.append(f"            self.close_all()")
        
    return "\n".join(lines)
