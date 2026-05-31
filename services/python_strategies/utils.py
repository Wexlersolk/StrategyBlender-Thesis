from __future__ import annotations

import re
from pathlib import Path
from .models import ENGINE_STRATEGY_DIR, SPEC_DIR

SYMBOL_ALIASES = {
    "US30": "US30.cash",
    "US30.CASH": "US30.cash",
    "US500": "US500.cash",
    "US500.CASH": "US500.cash",
    "US100": "US100.cash",
    "US100.CASH": "US100.cash",
    "NAS100": "US100.cash",
    "NASDAQ": "US100.cash",
    "NASDAQ100": "US100.cash",
    "NAS100.CASH": "US100.cash",
    "HK50": "HK50.cash",
    "HK50.CASH": "HK50.cash",
    "GER40": "GER40.cash",
    "GER40.CASH": "GER40.cash",
    "UK100": "UK100.cash",
    "UK100.CASH": "UK100.cash",
    "JP225": "JP225.cash",
    "JP225.CASH": "JP225.cash",
}
def symbol_dir_name(symbol: str) -> str:
    return str(symbol or "").strip().replace(".cash", "").replace(".", "_")

def generated_strategy_dir(symbol: str | None, timeframe: str | None) -> Path:
    sym = symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    if sym and tf:
        return ENGINE_STRATEGY_DIR / sym / tf
    return ENGINE_STRATEGY_DIR

def generated_spec_dir(symbol: str | None, timeframe: str | None) -> Path:
    sym = symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    if sym and tf:
        return SPEC_DIR / sym / tf
    return SPEC_DIR

def generated_strategy_module(symbol: str | None, timeframe: str | None, slug_base: str) -> str:
    sym = symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    if sym and tf:
        return f"strategies.generated.{sym}.{tf}.{slug_base}"
    return f"strategies.generated.{slug_base}"

def canonical_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    return SYMBOL_ALIASES.get(raw.upper(), raw)

def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "strategy"

def class_name_from_slug(slug: str) -> str:
    base = "".join(part.capitalize() for part in slug.split("_")) or "GeneratedStrategy"
    if not base[0].isalpha():
        base = f"Generated{base}"
    return base
