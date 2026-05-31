from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .python_strategies.models import (
    StrategySpec, CompiledStrategy, StrategyTemplate, IndicatorSpec,
    SeriesSpec, EntryRuleSpec, ExitRuleSpec, PRESET_DIR, ENGINE_STRATEGY_DIR,
    COMPUTE_ALLOWED_NAMES, ON_BAR_ALLOWED_NAMES, TEMPLATE_REGISTRY
)
from .python_strategies.utils import (
    canonical_symbol, slugify, class_name_from_slug,
    generated_strategy_dir, generated_spec_dir, generated_strategy_module
)
from .python_strategies.validator import validate_expression
from .python_strategies.renderer import (
    render_indicator, render_optional_numeric, render_strategy_code, serialize_spec
)
from .python_strategies import builders

# Target symbols for builder universe
TARGET_BUILD_UNIVERSE: tuple[str, ...] = (
    "USDJPY",
    "EURUSD",
    "GBPJPY",
    "XAUUSD",
    "US30.cash",
    "US500.cash",
    "US100.cash",
    "HK50.cash",
    "GER40.cash",
    "UK100.cash",
    "AUDUSD",
    "USDCAD",
)

def _template_matches_symbol(template: StrategyTemplate, symbol: str) -> bool:
    canonical = canonical_symbol(symbol)
    return not template.supported_symbols or canonical in template.supported_symbols


def _template_matches_timeframe(template: StrategyTemplate, timeframe: str) -> bool:
    normalized = str(timeframe or "").strip().upper()
    return not template.supported_timeframes or normalized in [str(item).strip().upper() for item in template.supported_timeframes]


def template_supports_market(template_name: str, symbol: str, timeframe: str | None = None) -> bool:
    template = TEMPLATE_REGISTRY.get(template_name)
    if template is None:
        return False
    if not _template_matches_symbol(template, symbol):
        return False
    if timeframe is not None and not _template_matches_timeframe(template, timeframe):
        return False
    return True

def template_profile(template_name: str) -> dict[str, Any] | None:
    template = TEMPLATE_REGISTRY.get(template_name)
    if template is None:
        return None
    return {
        "name": template.name,
        "description": template.description,
        "family": template.family,
        "regime": template.regime,
        "supported_symbols": list(template.supported_symbols),
        "supported_timeframes": list(template.supported_timeframes),
        "preferred_timeframes": list(template.preferred_timeframes),
        "sort_order": int(template.sort_order),
    }

def template_profiles(symbol: str | None = None) -> list[dict[str, Any]]:
    templates = list(TEMPLATE_REGISTRY.values())
    if symbol:
        templates = [template for template in templates if _template_matches_symbol(template, symbol)]
    templates.sort(key=lambda item: (item.sort_order, item.name))
    return [template_profile(template.name) for template in templates if template_profile(template.name)]

def available_builder_symbols() -> list[str]:
    return list(TARGET_BUILD_UNIVERSE)

def available_template_names(symbol: str | None = None) -> list[str]:
    names = [
        template.name
        for template in TEMPLATE_REGISTRY.values()
        if symbol is None or _template_matches_symbol(template, symbol)
    ]
    return [item for item in sorted(names, key=lambda name: (TEMPLATE_REGISTRY[name].sort_order, name))]

def strategy_spec_from_template(template_name: str, payload: dict[str, Any]) -> StrategySpec:
    template = TEMPLATE_REGISTRY.get(template_name)
    if template is None:
        supported = ", ".join(available_template_names())
        raise ValueError(f"Unknown strategy template: {template_name}. Supported templates: {supported}")
    symbol = canonical_symbol(str(payload.get("symbol", "")))
    if template.supported_symbols and symbol not in [canonical_symbol(s) for s in template.supported_symbols]:
        import os
        if os.environ.get("SKIP_TEMPLATE_SYMBOL_CHECK") == "1":
            pass # Allow for market scans
        else:
            raise ValueError(f"Template {template_name} is not configured for symbol {symbol}. Supported: {template.supported_symbols}")
    timeframe = str(payload.get("timeframe", "")).upper()
    if template.supported_timeframes and timeframe not in [str(item).strip().upper() for item in template.supported_timeframes]:
        raise ValueError(f"Template {template_name} is not configured for timeframe {timeframe}. Supported: {template.supported_timeframes}")
    payload = {**payload, "symbol": symbol or payload.get("symbol", "")}
    return template.build(payload)

def available_presets(symbol: str | None = None, template_name: str | None = None) -> list[dict[str, Any]]:
    presets: list[dict[str, Any]] = []
    if not PRESET_DIR.exists():
        return presets

    for path in sorted(PRESET_DIR.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        preset_template = payload.get("template")
        if preset_template not in TEMPLATE_REGISTRY:
            continue
        preset_payload = payload.get("payload", {})
        preset_symbol = canonical_symbol(str(preset_payload.get("symbol", "")))
        if symbol and preset_symbol != canonical_symbol(symbol):
            continue
        if template_name and preset_template != template_name:
            continue
        presets.append(
            {
                "id": path.stem,
                "path": str(path),
                "label": payload.get("label", path.stem.replace("_", " ").title()),
                "description": payload.get("description", ""),
                "template": preset_template,
                "payload": {**preset_payload, "symbol": preset_symbol or preset_payload.get("symbol", "")},
            }
        )
    return presets

def preset_by_id(preset_id: str) -> dict[str, Any] | None:
    for preset in available_presets():
        if preset["id"] == preset_id:
            return preset
    return None

def strategy_spec_from_dict(payload: dict[str, Any]) -> StrategySpec:
    return StrategySpec(
        name=payload["name"],
        symbol=payload["symbol"],
        timeframe=payload["timeframe"],
        params=payload.get("params", {}),
        indicators=[IndicatorSpec(**item) for item in payload.get("indicators", [])],
        series=[SeriesSpec(**item) for item in payload.get("series", [])],
        entries=[EntryRuleSpec(**item) for item in payload.get("entries", [])],
        exits=[ExitRuleSpec(**item) for item in payload.get("exits", [])],
        min_bars=int(payload.get("min_bars", 0)),
        lot_value=float(payload.get("lot_value", 1.0)),
        bar_time_offset_hours=float(payload.get("bar_time_offset_hours", 0.0)),
        allow_entries_when_position_open=bool(payload.get("allow_entries_when_position_open", False)),
        description=payload.get("description", ""),
    )

def _load_spec_payload(spec: StrategySpec | dict[str, Any]) -> StrategySpec:
    if isinstance(spec, StrategySpec):
        return spec
    return strategy_spec_from_dict(spec)

import re

def _patch_iloc(expr: str | None) -> str:
    if not expr:
        return ""
    expr = str(expr)
    expr = re.sub(r'\.shift\(1\)\.eq\(True\)\.iloc\[i\]', '.eq(True).iloc[i - 1]', expr)
    expr = re.sub(r'\.shift\(1\)\.iloc\[i\]', '.iloc[i - 1]', expr)
    expr = re.sub(r'\.shift\(1\)\.eq\(True\)\.iloc\[i - 1\]', '.eq(True).iloc[i - 1]', expr)
    expr = re.sub(r'\.shift\(1\)\.iloc\[i - 1\]', '.iloc[i - 1]', expr)
    return re.sub(r'\.iloc\[i\]', '.iloc[i - 1]', expr)

def compile_strategy_spec(
    spec: StrategySpec | dict[str, Any],
    *,
    strategy_id: str | None = None,
) -> CompiledStrategy:
    spec_obj = _load_spec_payload(spec)

    # Patch lookahead-biased .iloc[i] access
    for item in spec_obj.series:
        item.expression = _patch_iloc(item.expression)
    for item in spec_obj.entries:
        item.when = _patch_iloc(item.when)
        item.lots = _patch_iloc(item.lots)
        item.stop_loss = _patch_iloc(item.stop_loss)
        item.take_profit = _patch_iloc(item.take_profit)
        item.price = _patch_iloc(item.price)
        item.trail_dist = _patch_iloc(item.trail_dist)
        item.trail_activation = _patch_iloc(item.trail_activation)
    for item in spec_obj.exits:
        item.when = _patch_iloc(item.when)

    for item in spec_obj.series:
        validate_expression(item.expression, COMPUTE_ALLOWED_NAMES)

    for item in spec_obj.entries:
        validate_expression(item.when, ON_BAR_ALLOWED_NAMES)
        validate_expression(item.lots, ON_BAR_ALLOWED_NAMES)
        validate_expression(item.stop_loss, ON_BAR_ALLOWED_NAMES)
        validate_expression(item.take_profit, ON_BAR_ALLOWED_NAMES)
        if item.price:
            validate_expression(item.price, ON_BAR_ALLOWED_NAMES)
        if item.trail_dist:
            validate_expression(item.trail_dist, ON_BAR_ALLOWED_NAMES)
        if item.trail_activation:
            validate_expression(item.trail_activation, ON_BAR_ALLOWED_NAMES)
        if item.side not in {"long", "short"}:
            raise ValueError(f"Unsupported entry side: {item.side}")
        if item.order_type not in {"market", "buy_stop", "sell_stop", "buy_limit", "sell_limit"}:
            raise ValueError(f"Unsupported order type: {item.order_type}")

    for item in spec_obj.exits:
        validate_expression(item.when, ON_BAR_ALLOWED_NAMES)
        if item.action not in {"close_all", "cancel_pending"}:
            raise ValueError(f"Unsupported exit action: {item.action}")

    slug_base = slugify(f"{spec_obj.name}_{strategy_id or spec_obj.symbol}_{spec_obj.timeframe}")
    class_name = class_name_from_slug(slug_base)
    strategy_path = generated_strategy_dir(spec_obj.symbol, spec_obj.timeframe) / f"{slug_base}.py"
    spec_path = generated_spec_dir(spec_obj.symbol, spec_obj.timeframe) / f"{slug_base}.json"

    indicator_lines: list[str] = []
    indicator_imports: set[str] = {"sma", "wma"}
    for indicator in spec_obj.indicators:
        lines, func_name = render_indicator(indicator)
        indicator_lines.extend(lines)
        indicator_imports.add(func_name)

    series_lines: list[str] = []
    for item in spec_obj.series:
        series_lines.append(f'        df[{item.name!r}] = {item.expression}')

    if not indicator_lines and not series_lines:
        compute_body = ["        return df"]
    else:
        compute_body = [*indicator_lines, *series_lines, "        return df"]

    exit_lines: list[str] = []
    for item in spec_obj.exits:
        action_line = "ctx.close_all()" if item.action == "close_all" else "ctx.cancel_pending()"
        exit_lines.extend(
            [
                f"        if {item.when}:",
                f"            {action_line}",
                "            return",
            ]
        )

    entry_lines: list[str] = []
    position_guard = "" if spec_obj.allow_entries_when_position_open else "        if ctx.has_position or ctx.has_pending:\n            return\n"
    for item in spec_obj.entries:
        order_key = (item.side, item.order_type)
        supported_orders = {
            ("long", "market"),
            ("short", "market"),
            ("long", "buy_stop"),
            ("short", "sell_stop"),
            ("long", "buy_limit"),
            ("short", "sell_limit"),
        }
        if order_key not in supported_orders:
            raise ValueError(f"Invalid side/order_type combination: {item.side}/{item.order_type}")

        method_name = {
            ("long", "market"): "buy_market",
            ("short", "market"): "sell_market",
            ("long", "buy_stop"): "buy_stop",
            ("short", "sell_stop"): "sell_stop",
            ("long", "buy_limit"): "buy_limit",
            ("short", "sell_limit"): "sell_limit",
        }[order_key]

        call_args = [
            f"                sl={item.stop_loss},",
            f"                tp={item.take_profit},",
            f"                lots={item.lots},",
        ]
        if item.price:
            call_args.append(f"                price={item.price},")
        if item.order_type != "market":
            call_args.append(f"                expiry_bars={int(item.expiry_bars)},")
        call_args.append(f"                comment={item.comment!r},")

        entry_lines.extend(
            [
                f"        if {item.when}:",
                f"            self._next_trail_dist = {item.trail_dist or '0.0'}",
                f"            self._next_trail_activation = {item.trail_activation or '0.0'}",
                f"            self._next_exit_after_bars = {render_optional_numeric(item.exit_after_bars)}",
                f"            ctx.{method_name}(",
                *call_args,
                "            )",
            ]
        )

    indicator_import_block = ", ".join(sorted(indicator_imports))
    if indicator_import_block:
        indicator_import_block = f"from engine.indicators import {indicator_import_block}"

    description_line = spec_obj.description or "Generated from StrategySpec."
    source_lines = [
        '"""',
        "Auto-generated Python strategy.",
        description_line,
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import numpy as np",
        "import pandas as pd",
        "",
        "from engine.base_strategy import BaseStrategy, BarContext",
    ]
    if indicator_import_block:
        source_lines.append(indicator_import_block)
        
    # Standard helper functions for generated strategies
    source_lines.extend([
        "", "",
        "def _count_compare(left: pd.Series, right: pd.Series, bars: int, shift: int = 0, *, greater: bool, allow_equal: bool) -> pd.Series:",
        "    lhs = left.shift(shift)",
        "    rhs = right.shift(shift)",
        "    if greater:",
        "        ok = lhs >= rhs if allow_equal else lhs > rhs",
        "    else:",
        "        ok = lhs <= rhs if allow_equal else lhs < rhs",
        "    return ok.rolling(int(bars), min_periods=int(bars)).sum().eq(int(bars))",
        "", "",
        "def _sq_count_compare(left: pd.Series, right: pd.Series, bars: int, shift: int = 0, *, greater: bool, not_strict: bool, rounding: int = 5) -> pd.Series:",
        "    comparisons = []",
        "    strict_hits = []",
        "    for offset in range(int(bars)):",
        "        lhs = left.shift(int(shift) + offset).round(int(rounding))",
        "        rhs = right.shift(int(shift) + offset).round(int(rounding))",
        "        if greater:",
        "            comparisons.append(lhs >= rhs if not_strict else lhs > rhs)",
        "            strict_hits.append(lhs > rhs)",
        "        else:",
        "            comparisons.append(lhs <= rhs if not_strict else lhs < rhs)",
        "            strict_hits.append(lhs < rhs)",
        "    all_ok = comparisons[0]",
        "    any_strict = strict_hits[0]",
        "    for item in comparisons[1:]:",
        "        all_ok = all_ok & item",
        "    for item in strict_hits[1:]:",
        "        any_strict = any_strict | item",
        "    return all_ok & any_strict",
        "", "",
        "def _sq_lower_percentile(series: pd.Series, percentile: float, bars: int, shift: int = 0, *, rounding: int = 5) -> pd.Series:",
        "    ref = series.astype(float).round(int(rounding))",
        "    out = pd.Series(False, index=series.index)",
        "    lookback = max(int(bars), 1)",
        "    start = int(shift) + lookback - 1",
        "    for idx in range(start, len(ref)):",
        "        curr = ref.iloc[idx - int(shift)]",
        "        if pd.isna(curr): continue",
        "        count = 1",
        "        for offset in range(lookback):",
        "            prev = ref.iloc[idx - int(shift) - offset]",
        "            if pd.isna(prev): continue",
        "            if curr < prev: count += 1",
        "        out.iloc[idx] = ((count / lookback) * 100.0) >= float(percentile)",
        "    return out",
        "", "",
        "def _cross_above(left: pd.Series, right: pd.Series | float) -> pd.Series:",
        "    rhs = right if isinstance(right, pd.Series) else pd.Series(float(right), index=left.index)",
        "    return (left.shift(1) <= rhs.shift(1)) & (left > rhs)",
        "", "",
        "def _cross_below(left: pd.Series, right: pd.Series | float) -> pd.Series:",
        "    rhs = right if isinstance(right, pd.Series) else pd.Series(float(right), index=left.index)",
        "    return (left.shift(1) >= rhs.shift(1)) & (left < rhs)",
        "", "",
        "def _compare_window(left: pd.Series, right: pd.Series, bars: int, shift: int, allow_same: bool, greater: bool) -> pd.Series:",
        "    lhs = left.shift(shift)",
        "    rhs = right.shift(shift)",
        "    if greater:",
        "        ok = lhs >= rhs if allow_same else lhs > rhs",
        "        strict = lhs > rhs",
        "    else:",
        "        ok = lhs <= rhs if allow_same else lhs < rhs",
        "        strict = lhs < rhs",
        "    return ok.rolling(int(bars), min_periods=int(bars)).sum().eq(int(bars)) & strict.rolling(int(bars), min_periods=int(bars)).sum().gt(0)",
        "", "",
        "def _falling(series: pd.Series, bars: int, shift: int = 0) -> pd.Series:",
        "    ref = series.shift(shift)",
        "    delta = ref.diff()",
        "    rolled = delta.rolling(int(bars), min_periods=int(bars)).apply(lambda values: float((values < 0).all()), raw=True)",
        "    return rolled.astype(float).fillna(0.0).gt(0.5)",
        "", "",
        "def _rising(series: pd.Series, bars: int, shift: int = 0) -> pd.Series:",
        "    ref = series.shift(shift)",
        "    delta = ref.diff()",
        "    rolled = delta.rolling(int(bars), min_periods=int(bars)).apply(lambda values: float((values > 0).all()), raw=True)",
        "    return rolled.astype(float).fillna(0.0).gt(0.5)",
        "", "",
        "def _hhmm(ts: pd.Timestamp) -> int:",
        "    return ts.hour * 100 + ts.minute",
        "", "",
        "def _in_time_window(ts: pd.Timestamp, start: str, end: str) -> bool:",
        "    start_hhmm = int(start[:2]) * 100 + int(start[3:])",
        "    end_hhmm = int(end[:2]) * 100 + int(end[3:])",
        "    current = _hhmm(ts)",
        "    if start_hhmm <= end_hhmm: return start_hhmm <= current <= end_hhmm",
        "    return current >= start_hhmm or current <= end_hhmm",
        "", "",
        f"class {class_name}(BaseStrategy):",
        f"    name = {spec_obj.name!r}",
        f"    symbol = {spec_obj.symbol!r}",
        f"    timeframe = {spec_obj.timeframe!r}",
        f"    lot_value = {float(spec_obj.lot_value)!r}",
        f"    bar_time_offset_hours = {float(spec_obj.bar_time_offset_hours)!r}",
        f"    params = {spec_obj.params!r}",
        "",
        "    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:",
        *compute_body,
        "",
        "    def on_start(self, df: pd.DataFrame):",
        "        self._next_trail_dist = 0.0",
        "        self._next_trail_activation = 0.0",
        "        self._next_exit_after_bars = 0",
        "",
        "    def on_bar(self, ctx: BarContext):",
        "        i = ctx.bar_index",
        "        df = ctx.df",
        f"        if i < {int(spec_obj.min_bars)}: return",
        *exit_lines,
    ])
    
    if position_guard:
        source_lines.extend(position_guard.rstrip("\n").splitlines())
        
    source_lines.extend(entry_lines or ["        return"])
    source_lines.append("")

    return CompiledStrategy(
        spec=spec_obj,
        strategy_slug=slug_base,
        strategy_class=class_name,
        strategy_module=generated_strategy_module(spec_obj.symbol, spec_obj.timeframe, slug_base),
        strategy_path=str(strategy_path),
        spec_path=str(spec_path),
        source="\n".join(source_lines),
    )

def persist_strategy_spec(compiled: CompiledStrategy) -> dict[str, str]:
    strategy_path = Path(compiled.strategy_path)
    spec_path = Path(compiled.spec_path)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    strategy_path.parent.mkdir(parents=True, exist_ok=True)
    
    current = strategy_path.parent
    while current == ENGINE_STRATEGY_DIR or ENGINE_STRATEGY_DIR in current.parents:
        init_path = current / "__init__.py"
        if not init_path.exists():
            init_path.write_text("", encoding="utf-8")
        if current == ENGINE_STRATEGY_DIR:
            break
        current = current.parent

    strategy_path.write_text(compiled.source, encoding="utf-8")
    spec_path.write_text(
        json.dumps(serialize_spec(compiled.spec), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "strategy_path": compiled.strategy_path,
        "spec_path": compiled.spec_path,
    }
