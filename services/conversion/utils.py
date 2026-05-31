from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONVERTED_DIR = ROOT / "convert" / "generated"
ENGINE_STRATEGY_DIR = ROOT / "strategies" / "generated"
MINE_INDICATORS_DIR = ROOT / "mine" / "Indicators"

PRICE_MODE_MAP = {
    "PRICE_CLOSE": 0,
    "PRICE_OPEN": 1,
    "PRICE_HIGH": 2,
    "PRICE_LOW": 3,
    "PRICE_MEDIAN": 4,
    "PRICE_TYPICAL": 5,
    "PRICE_WEIGHTED": 6,
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "strategy"


def class_name_from_slug(slug: str) -> str:
    base = "".join(part.capitalize() for part in slug.split("_")) or "GeneratedStrategy"
    if not base[0].isalpha():
        base = f"Generated{base}"
    return base


def normalize_symbol(symbol: str) -> str:
    if not symbol:
        return symbol

    cleaned = re.sub(r"\([^)]*\)", "", symbol).strip()
    upper = cleaned.upper()

    direct_map = {
        "HKG50_MT5IMPORT": "HK50.cash",
        "HK50": "HK50.cash",
        "HK50.CASH": "HK50.cash",
        "US30_MT5": "US30.cash",
        "US30.CASH": "US30.cash",
        "XAUUSD_FTMO": "XAUUSD",
        "USDJPY_FTMO": "USDJPY",
    }
    if upper in direct_map:
        return direct_map[upper]

    suffixes = ["_FTMO", ".FTMO", "_MT5", ".MT5", "_CASH", ".CASH"]
    for suffix in suffixes:
        if upper.endswith(suffix):
            upper = upper[: -len(suffix)]
            break

    if upper == "HK50":
        return "HK50.cash"
    if upper == "US30":
        return "US30.cash"
    if upper in {"XAUUSD", "XAGUSD", "USDJPY", "EURUSD", "GBPUSD", "EURJPY"}:
        return upper
    return cleaned


def _symbol_dir_name(symbol: str) -> str:
    return str(symbol or "").strip().replace(".cash", "").replace(".", "_")


def _generated_strategy_dir(symbol: str | None, timeframe: str | None) -> Path:
    sym = _symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    if sym and tf:
        return ENGINE_STRATEGY_DIR / sym / tf
    return ENGINE_STRATEGY_DIR


def _generated_strategy_module(symbol: str | None, timeframe: str | None, slug_base: str) -> str:
    sym = _symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    if sym and tf:
        return f"strategies.generated.{sym}.{tf}.{slug_base}"
    return f"strategies.generated.{slug_base}"


def _infer_lot_value(symbol: str) -> float:
    symbol = normalize_symbol(symbol)
    mapping = {
        "HK50.cash": 0.1285,
        "US30.cash": 1.0,
        "US100.cash": 1.0,
        "US500.cash": 1.0,
        "GER40.cash": 1.0,
        "JP225.cash": 1.0,
        "UK100.cash": 1.0,
        "XAUUSD": 100.0,
        "XAGUSD": 5000.0,
    }
    return mapping.get(symbol, 1.0)
