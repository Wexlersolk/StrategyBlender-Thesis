from __future__ import annotations

from pathlib import Path
from typing import Any

from config import settings

ROOT = Path(__file__).resolve().parent.parent.parent
MT5_GENERATED_DIR = ROOT / "mt5" / "generated"
MT5_SHORTLIST_DIR = ROOT / "mt5" / "shortlist"
MT5_ROOT_DIR = ROOT / "mt5"


def mql_broker_tradable_checks(symbol: str) -> str:
    defaults = settings.symbol_execution_defaults(symbol)
    windows = defaults.get("tradable_session_windows", {})
    if not windows:
        return "   return true;"

    lines: list[str] = []
    for day in sorted(windows):
        day_windows = windows.get(day, [])
        if not day_windows:
            continue
        conditions = []
        for start, end in day_windows:
            start_hhmm = int(str(start)[:2]) * 100 + int(str(start)[3:])
            end_hhmm = int(str(end)[:2]) * 100 + int(str(end)[3:])
            conditions.append(f"(hhmm >= {start_hhmm} && hhmm <= {end_hhmm})")
        joined = " || ".join(conditions)
        lines.append(f"   if(dt.day_of_week == {int(day)} && ({joined}))")
        lines.append("      return true;")
    lines.append("   return false;")
    return "\n".join(lines)


def symbol_dir_name(symbol: str) -> str:
    return str(symbol or "").strip().replace(".cash", "").replace(".", "_")


def mt5_collection_dir(collection: str | None = None) -> Path:
    normalized = str(collection or "generated").strip().lower()
    if normalized == "shortlist":
        return MT5_SHORTLIST_DIR
    if normalized == "generated":
        return MT5_GENERATED_DIR
    return MT5_ROOT_DIR / normalized


def mt5_output_dir(symbol: str | None, timeframe: str | None, strategy_slug: str, *, collection: str | None = None) -> Path:
    sym = symbol_dir_name(str(symbol or ""))
    tf = str(timeframe or "").strip().upper()
    base_dir = mt5_collection_dir(collection)
    if sym and tf:
        return base_dir / sym / tf / strategy_slug
    return base_dir / strategy_slug


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def session_hours(session_filter: str) -> tuple[int, int]:
    mapping = {
        "all_day": (0, 23),
        "london_only": (6, 11),
        "ny_only": (12, 18),
        "london_ny": (6, 18),
    }
    return mapping.get(session_filter, (6, 18))


def signal_window_params(
    symbol: str | None,
    params: dict[str, Any],
    *,
    default_from: str,
    default_to: str,
) -> tuple[str, str]:
    return (
        str(params.get("SignalTimeRangeFrom", default_from)),
        str(params.get("SignalTimeRangeTo", default_to)),
    )


def normalized_export_lots(symbol: str | None, params: dict[str, Any], *, default: float, payload: dict[str, Any] | None = None) -> float:
    val = params.get("mmLots", default)
    return parse_float(val, default)


def magic_number(strategy_id: str) -> int:
    digits = "".join(ch for ch in strategy_id if ch.isdigit())
    if not digits:
        return 1100001
    return int(digits[-7:])


def mt5_timeframe(tf: str | None) -> str:
    tf_str = str(tf or "H1").upper()
    mapping = {
        "M1": "PERIOD_M1",
        "M5": "PERIOD_M5",
        "M15": "PERIOD_M15",
        "M30": "PERIOD_M30",
        "H1": "PERIOD_H1",
        "H4": "PERIOD_H4",
        "D1": "PERIOD_D1",
    }
    return mapping.get(tf_str, "PERIOD_H1")


def mql_session_window_checks(windows: dict[int, list[tuple[str, str]]]) -> str:
    lines: list[str] = []
    for day in sorted(windows):
        day_windows = windows.get(day, [])
        if not day_windows:
            continue
        conditions = []
        for start, end in day_windows:
            start_hhmm = int(str(start)[:2]) * 100 + int(str(start)[3:])
            end_hhmm = int(str(end)[:2]) * 100 + int(str(end)[3:])
            conditions.append(f"(hhmm >= {start_hhmm} && hhmm <= {end_hhmm})")
        joined = " || ".join(conditions)
        lines.append(f"   if(dt.day_of_week == {int(day)} && ({joined}))")
        lines.append("      return true;")
    if not lines:
        lines.append("   return true;")
    else:
        lines.append("   return false;")
    return "\n".join(lines)
