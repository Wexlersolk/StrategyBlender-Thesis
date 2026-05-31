from __future__ import annotations

import re
from typing import Any

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
def canonical_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    return SYMBOL_ALIASES.get(raw.upper(), raw)

def required(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in payload:
        return payload[key]
    if default is not None:
        return default
    raise ValueError(f"Missing required template field: {key}")


def param_payload(_payload: dict[str, Any], key: str, multiplier: float | None = None) -> dict[str, Any]:
    res: dict[str, Any] = {"param": str(key)}
    if multiplier is not None:
        res["multiplier"] = float(multiplier)
    return res


def direction_mode(payload: dict[str, Any]) -> str:
    mode = str(payload.get("direction_mode", "both")).strip().lower() or "both"
    if mode in {"long_and_short", "balanced"}:
        mode = "both"
    if mode not in {"both", "long_only", "short_only"}:
        raise ValueError(f"Unsupported direction_mode: {mode}")
    return mode
