from __future__ import annotations

from pathlib import Path
import re
from typing import Any


def _html_lines(report_path: str | Path) -> list[str]:
    path = Path(report_path)
    html = path.read_text(encoding="utf-16", errors="ignore")
    text = re.sub(r"<[^>]+>", "\n", html)
    return [line.strip() for line in text.splitlines() if line.strip()]


def mt5_validation_acceptance(
    mt5_metrics: dict[str, float | int | str],
    *,
    min_trades: int,
    min_profit_factor: float,
    max_drawdown_pct: float,
) -> bool:
    trades = int(mt5_metrics.get("total_trades", 0) or 0)
    pf = float(mt5_metrics.get("profit_factor", 0.0) or 0.0)
    dd = float(mt5_metrics.get("equity_drawdown_relative_pct", 0.0) or 0.0)
    return (
        trades >= int(min_trades)
        and pf >= float(min_profit_factor)
        and dd <= float(max_drawdown_pct)
    )


def parse_mt5_report(report_path: str | Path) -> dict[str, float | int | str]:
    lines = _html_lines(report_path)

    pairs: dict[str, str] = {}
    for idx, line in enumerate(lines[:-1]):
        if line.endswith(":"):
            pairs[line[:-1]] = lines[idx + 1]

    def _num(key: str) -> float:
        raw = pairs.get(key, "").replace(" ", "").replace(",", "").replace("%", "")
        raw = raw.split("(")[0]
        try:
            return float(raw)
        except ValueError:
            return 0.0

    def _int(key: str) -> int:
        return int(round(_num(key)))

    def _metric_pair(key: str) -> tuple[float, float]:
        raw = pairs.get(key, "").replace(" ", "").replace(",", "")
        match = re.match(r"([-0-9.]+)(?:\(([-0-9.]+)%\))?", raw)
        if not match:
            return 0.0, 0.0
        primary = float(match.group(1))
        secondary = float(match.group(2)) if match.group(2) is not None else 0.0
        return primary, secondary

    profit_trades, win_rate_pct = _metric_pair("Profit Trades (% of total)")
    loss_trades, loss_rate_pct = _metric_pair("Loss Trades (% of total)")
    short_trades, short_win_pct = _metric_pair("Short Trades (won %)")
    long_trades, long_win_pct = _metric_pair("Long Trades (won %)")
    z_score, z_score_probability_pct = _metric_pair("Z-Score")
    ahpr, ahpr_pct = _metric_pair("AHPR")
    ghpr, ghpr_pct = _metric_pair("GHPR")

    return {
        "expert": pairs.get("Expert", ""),
        "symbol": pairs.get("Symbol", ""),
        "period": pairs.get("Period", ""),
        "company": pairs.get("Company", ""),
        "currency": pairs.get("Currency", ""),
        "initial_deposit": _num("Initial Deposit"),
        "history_quality": _num("History Quality"),
        "total_net_profit": _num("Total Net Profit"),
        "profit_factor": _num("Profit Factor"),
        "balance_drawdown_relative_pct": _num("Balance Drawdown Relative"),
        "equity_drawdown_relative_pct": _num("Equity Drawdown Relative"),
        "sharpe_ratio": _num("Sharpe Ratio"),
        "total_trades": _int("Total Trades"),
        "profit_trades": int(round(profit_trades)),
        "loss_trades": int(round(loss_trades)),
        "win_rate_pct": win_rate_pct,
        "loss_rate_pct": loss_rate_pct,
        "expected_payoff": _num("Expected Payoff"),
        "recovery_factor": _num("Recovery Factor"),
        "z_score": z_score,
        "z_score_probability_pct": z_score_probability_pct,
        "ahpr": ahpr,
        "ahpr_pct": ahpr_pct,
        "ghpr": ghpr,
        "ghpr_pct": ghpr_pct,
        "lr_correlation": _num("LR Correlation"),
        "short_trades": int(round(short_trades)),
        "short_win_pct": short_win_pct,
        "long_trades": int(round(long_trades)),
        "long_win_pct": long_win_pct,
    }


def parse_mt5_deal_rows(report_path: str | Path) -> list[dict[str, Any]]:
    html = Path(report_path).read_text(encoding="utf-16", errors="ignore")
    start = html.find("<b>Deals</b>")
    if start < 0:
        return []
    end = html.find("<b>Open Positions</b>", start)
    if end < 0:
        end = len(html)
    section = html[start:end]
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    cell_re = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
    rows: list[dict[str, Any]] = []
    for match in row_re.finditer(section):
        row_html = match.group(1)
        cells = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cell_re.findall(row_html)]
        if len(cells) != 13:
            continue
        if not re.match(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        rows.append(
            {
                "time": cells[0],
                "deal": cells[1],
                "symbol": cells[2],
                "type": cells[3].lower(),
                "direction": cells[4].lower(),
                "volume": cells[5],
                "price": cells[6],
                "order": cells[7],
                "commission": cells[8],
                "swap": cells[9],
                "profit": cells[10],
                "balance": cells[11],
                "comment": cells[12],
            }
        )
    return rows


def parse_mt5_trade_sequence(report_path: str | Path, *, strategy_tag: str) -> list[dict[str, Any]]:
    deals = parse_mt5_deal_rows(report_path)
    sequence: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for row in deals:
        direction = row.get("direction", "")
        comment = str(row.get("comment", ""))
        row_type = str(row.get("type", "")).lower()
        
        if direction == "in":
            if strategy_tag in comment:
                is_long_entry = row_type == "buy"
                current = {
                    "entry_time": row.get("time"),
                    "entry_side": "long" if is_long_entry else "short",
                    "entry_type": row_type,
                    "entry_price": row.get("price"),
                    "mt5_entry_comment": comment,
                }
            continue
            
        if direction == "out" and current is not None:
            current["exit_time"] = row.get("time")
            current["exit_price"] = row.get("price")
            current["exit_type"] = row_type
            current["mt5_exit_comment"] = comment
            current["profit"] = row.get("profit")
            sequence.append(current)
            current = None
            
    return sequence


def compare_mt5_to_native(mt5_metrics: dict[str, float | int | str], native_backtest: dict[str, float | int | str]) -> dict[str, float]:
    native_profit = float(native_backtest.get("total_profit", 0.0) or 0.0)
    native_pf = float(native_backtest.get("profit_factor", 0.0) or 0.0)
    native_dd = float(native_backtest.get("equity_dd_pct", native_backtest.get("max_drawdown_pct", 0.0)) or 0.0)
    native_trades = float(native_backtest.get("num_trades", 0.0) or 0.0)

    mt5_profit = float(mt5_metrics.get("total_net_profit", 0.0) or 0.0)
    mt5_pf = float(mt5_metrics.get("profit_factor", 0.0) or 0.0)
    mt5_dd = float(mt5_metrics.get("equity_drawdown_relative_pct", 0.0) or 0.0)
    mt5_trades = float(mt5_metrics.get("total_trades", 0.0) or 0.0)

    return {
        "profit_ratio_mt5_to_native": (mt5_profit / native_profit) if abs(native_profit) > 1e-9 else 0.0,
        "profit_factor_ratio_mt5_to_native": (mt5_pf / native_pf) if abs(native_pf) > 1e-9 else 0.0,
        "drawdown_ratio_mt5_to_native": (mt5_dd / native_dd) if abs(native_dd) > 1e-9 else 0.0,
        "trade_count_ratio_mt5_to_native": (mt5_trades / native_trades) if abs(native_trades) > 1e-9 else 0.0,
    }


def mt5_correlation_acceptance(
    comparison: dict[str, float],
    *,
    min_profit_ratio: float = 0.7,
    min_profit_factor_ratio: float = 0.75,
    min_trade_count_ratio: float = 0.8,
    max_trade_count_ratio: float = 1.25,
    max_drawdown_ratio: float = 2.5,
) -> bool:
    profit_ratio = float(comparison.get("profit_ratio_mt5_to_native", 0.0) or 0.0)
    pf_ratio = float(comparison.get("profit_factor_ratio_mt5_to_native", 0.0) or 0.0)
    dd_ratio = float(comparison.get("drawdown_ratio_mt5_to_native", 0.0) or 0.0)
    trades_ratio = float(comparison.get("trade_count_ratio_mt5_to_native", 0.0) or 0.0)
    return (
        profit_ratio >= min_profit_ratio
        and pf_ratio >= min_profit_factor_ratio
        and min_trade_count_ratio <= trades_ratio <= max_trade_count_ratio
        and dd_ratio <= max_drawdown_ratio
    )


def compare_trade_sequences(native_trades: list[dict[str, Any]], mt5_trades: list[dict[str, Any]], *, limit: int = 30) -> dict[str, Any]:
    import pandas as pd
    compared: list[dict[str, Any]] = []
    divergence: dict[str, Any] | None = None
    n = min(limit, len(native_trades), len(mt5_trades))
    for idx in range(n):
        native = native_trades[idx]
        mt5 = mt5_trades[idx]
        issue = "aligned"
        
        native_entry = pd.Timestamp(native.get("entry_time"))
        mt5_entry_str = str(mt5.get("entry_time", "")).replace(".", "-")
        mt5_entry = pd.Timestamp(mt5_entry_str) if mt5_entry_str else pd.Timestamp("1970-01-01")
        
        native_exit = pd.Timestamp(native.get("exit_time"))
        mt5_exit_str = str(mt5.get("exit_time", "")).replace(".", "-")
        mt5_exit = pd.Timestamp(mt5_exit_str) if mt5_exit_str else pd.Timestamp("1970-01-01")

        # Allow up to 1 hour difference for entry (intrabar triggers)
        entry_diff = abs((native_entry - mt5_entry).total_seconds())
        exit_diff = abs((native_exit - mt5_exit).total_seconds())

        if native.get("entry_side") != mt5.get("entry_side"):
            issue = "signal_generation"
        elif entry_diff > 3600:
            issue = "signal_generation"
        elif exit_diff > 3600:
            mt5_comment = str(mt5.get("mt5_exit_comment", "")).lower()
            if "sl" in mt5_comment or "tp" in mt5_comment:
                issue = "stop_tp_handling"
            elif mt5_exit.hour == 18 or native_exit.hour == 18:
                issue = "session_exit_timing"
            else:
                issue = "order_lifecycle"
        compared.append(
            {
                "index": idx,
                "issue": issue,
                "native": native,
                "mt5": mt5,
            }
        )
        if divergence is None and issue != "aligned":
            divergence = compared[-1]
            break
    return {
        "compared": compared,
        "first_divergence": divergence,
        "native_trades": len(native_trades),
        "mt5_trades": len(mt5_trades),
    }
