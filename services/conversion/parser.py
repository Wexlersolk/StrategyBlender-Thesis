from __future__ import annotations

import re

from services.conversion.utils import MINE_INDICATORS_DIR, PRICE_MODE_MAP


def _find_param(params: dict, *patterns: str, default=None):
    lowered = {k.lower(): k for k in params}
    for pattern in patterns:
        for low_name, original in lowered.items():
            if pattern in low_name:
                return params[original]
    return default


def _find_int_literal(source: str, pattern: str, default: int) -> int:
    match = re.search(pattern, source, re.IGNORECASE)
    if not match:
        return default
    return int(match.group(1))


def _split_mql_args(args: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_string = False

    for char in args:
        if char == '"':
            in_string = not in_string
        if char == "," and not in_string:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    if current:
        parts.append("".join(current).strip())

    return parts


def _find_icustom_args(source: str, indicator_name: str, define_name: str | None = None) -> list[str] | None:
    if define_name:
        pattern = re.compile(
            rf"#define\s+{re.escape(define_name)}\s+\d+\s+//iCustom\((?P<args>[^\n]+)\)",
            re.IGNORECASE,
        )
        match = pattern.search(source)
        if match:
            args = _split_mql_args(match.group("args"))
            if len(args) >= 3:
                return args[3:]

    pattern = re.compile(
        rf'iCustom\((?P<args>[^\n;]*"{re.escape(indicator_name)}"[^\n;]*)\)',
        re.IGNORECASE,
    )
    match = pattern.search(source)
    if not match:
        return None
    args = _split_mql_args(match.group("args"))
    if len(args) < 3:
        return None
    return args[3:]


def _resolve_mql_numeric(arg: str, default: int) -> int:
    arg = arg.strip()
    if arg in PRICE_MODE_MAP:
        return PRICE_MODE_MAP[arg]
    try:
        return int(float(arg))
    except ValueError:
        return default


def _resolve_mql_float(arg: str, default: float) -> float:
    arg = arg.strip()
    try:
        return float(arg)
    except ValueError:
        return default


def _find_define_call_args(source: str, define_name: str, function_name: str) -> list[str] | None:
    pattern = re.compile(
        rf"#define\s+{re.escape(define_name)}\s+\d+\s+//{re.escape(function_name)}\((?P<args>[^\n]+)\)",
        re.IGNORECASE,
    )
    match = pattern.search(source)
    if not match:
        return None
    return _split_mql_args(match.group("args"))


def _extract_ima_spec(
    source: str,
    define_name: str,
    defaults: tuple[int, int],
) -> tuple[int, int]:
    args = _find_define_call_args(source, define_name, "iMA")
    if not args or len(args) < 6:
        return defaults
    return (
        _resolve_mql_numeric(args[2], defaults[0]),
        _resolve_mql_numeric(args[5], defaults[1]),
    )


def _extract_ibands_spec(
    source: str,
    define_name: str,
    defaults: tuple[int, float, int],
) -> tuple[int, float, int]:
    args = _find_define_call_args(source, define_name, "iBands")
    if not args or len(args) < 6:
        return defaults
    return (
        _resolve_mql_numeric(args[2], defaults[0]),
        _resolve_mql_float(args[4], defaults[1]),
        _resolve_mql_numeric(args[5], defaults[2]),
    )


def _extract_iosma_spec(
    source: str,
    define_name: str,
    defaults: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    args = _find_define_call_args(source, define_name, "iOsMA")
    if not args or len(args) < 6:
        return defaults
    return (
        _resolve_mql_numeric(args[2], defaults[0]),
        _resolve_mql_numeric(args[3], defaults[1]),
        _resolve_mql_numeric(args[4], defaults[2]),
        _resolve_mql_numeric(args[5], defaults[3]),
    )


def _extract_indicator_spec(
    source: str,
    indicator_name: str,
    define_name: str | None,
    defaults: tuple[int, ...],
) -> tuple[int, ...]:
    args = _find_icustom_args(source, indicator_name, define_name)
    if not args:
        return defaults

    resolved = list(defaults)
    for idx, default in enumerate(defaults):
        if idx >= len(args):
            break
        resolved[idx] = _resolve_mql_numeric(args[idx], default)
    return tuple(resolved)


def _extract_string_input(source: str, name: str, default: str = "") -> str:
    match = re.search(
        rf'input\s+string\s+{re.escape(name)}\s*=\s*"([^"]*)"',
        source,
        re.IGNORECASE,
    )
    return match.group(1) if match else default


def _extract_bool_input(source: str, name: str, default: bool = False) -> bool:
    match = re.search(
        rf"input\s+bool\s+{re.escape(name)}\s*=\s*(true|false)",
        source,
        re.IGNORECASE,
    )
    if not match:
        return default
    return match.group(1).lower() == "true"


def _indicator_port_available(indicator_name: str) -> bool:
    return (MINE_INDICATORS_DIR / f"{indicator_name}.mq5").exists()


def _extract_custom_indicator_names(source: str) -> list[str]:
    found: set[str] = set()
    for match in re.finditer(r'#define\s+\w+\s+\d+\s+//iCustom\([^\n;]*?"([^"]+)"', source):
        found.add(match.group(1))
    for match in re.finditer(r'indicatorHandles\[[^\]]+\]\s*=\s*iCustom\([^\n;]*?"([^"]+)"', source):
        found.add(match.group(1))
    return sorted(found)
