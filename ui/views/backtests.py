"""
ui/views/backtests.py

Strategy conversion workspace:
- shows generated local Python review scaffolds for uploaded MT5 EAs
- allows exporting converted files
- runs local backtests on generated engine strategies using exported MT5 data
"""

from pathlib import Path

import importlib
import sys

import pandas as pd
import streamlit as st

from ui.components.common import section_header, empty_state
from ui.components.backtest_viewer import render_individual_results, render_portfolio_analysis
from ui.state import autosave
from services.backtest_service import (
    available_backtest_symbols,
    backtest_result_payload,
    default_execution_config,
    run_backtest,
)
from services.conversion.utils import normalize_symbol
from services.conversion_service import convert_ea_source, persist_converted_ea


GENERATED_DIR = Path(__file__).parent.parent.parent / "convert" / "generated"


def render():
    section_header("Backtests", "Convert MT5 EAs and run them on local market data")

    eas = st.session_state.get("eas", {})

    tab_convert, tab_results, tab_portfolio = st.tabs([
        "🔁 MT5 -> Python", "📊 Individual Results", "📈 Portfolio View"
    ])

    with tab_convert:
        _render_conversion_tab(eas)

    with tab_results:
        results = st.session_state.get("backtest_results", {})
        render_individual_results(eas, results)

    with tab_portfolio:
        results = st.session_state.get("backtest_results", {})
        if len(results) < 2:
            st.info(
                "Add backtest results for at least 2 strategies to see portfolio analytics.",
                icon="ℹ️",
            )
        else:
            render_portfolio_analysis(eas, results)


def _render_conversion_tab(eas: dict):
    st.markdown("#### Conversion and execution flow")
    st.info(
        "**MT5 path** — Upload your `.mq5` EA in `EA Manager` and StrategyBlender converts it into "
        "local Python artifacts.\n\n"
        "**Native Python path** — Use `Strategy Builder` to generate a strategy family directly from "
        "templates and presets.\n\n"
        "**Execution** — Run either type below against the local market data already stored in "
        "`data/exports/MT5 data export/`.",
        icon="ℹ️",
    )

    if not eas:
        empty_state("No EAs loaded yet. Upload a `.mq5` file in EA Manager first.", "🤖")
        return

    st.markdown(f"Generated files are written to `{GENERATED_DIR}` and `strategies/generated/`.")

    ea_options = {
        ea_id: f"{ea['name']} — {ea['symbol']} {ea['timeframe']}"
        for ea_id, ea in eas.items()
    }
    selected = st.selectbox(
        "Select converted EA",
        list(ea_options.keys()),
        format_func=lambda x: ea_options[x],
    )
    ea = eas[selected]
    review_source = ea.get("review_source") or ea.get("python_source", "")
    engine_source = ea.get("engine_source", "")

    col1, col2, col3 = st.columns(3)
    col1.metric("Inputs", len(ea.get("params", {})))
    col2.metric("Functions", len(ea.get("conversion_functions", [])))
    col3.metric("Warnings", len(ea.get("conversion_warnings", [])))

    if ea.get("conversion_warnings"):
        for warning in ea["conversion_warnings"]:
            st.warning(warning, icon="⚠️")

    available_syms = available_backtest_symbols(ea["timeframe"])
    default_symbol = ea["symbol"] if ea["symbol"] in available_syms else available_syms[0]
    default_idx = available_syms.index(default_symbol)

    st.markdown("##### Run local backtest")
    col_cfg_1, col_cfg_2, col_cfg_3 = st.columns(3)
    with col_cfg_1:
        run_symbol = st.selectbox(
            "Symbol",
            available_syms,
            index=default_idx,
            key=f"run_symbol_{selected}",
        )
    with col_cfg_2:
        date_from = st.date_input(
            "From",
            value=pd.Timestamp("2020-01-01"),
            key=f"run_from_{selected}",
        )
    with col_cfg_3:
        date_to = st.date_input(
            "To",
            value=pd.Timestamp("2025-12-31"),
            key=f"run_to_{selected}",
        )

    intrabar = st.checkbox(
        "Use actual M1 intrabar data",
        value=False,
        key=f"intrabar_{selected}",
        help="Replays real minute bars inside each higher-timeframe candle when M1 export data is available.",
    )
    default_execution = default_execution_config(run_symbol)
    st.markdown("##### Execution model")
    st.caption("XAUUSD defaults use conservative commission/slippage and can use the MT5 spread column when available.")
    exec_col_1, exec_col_2, exec_col_3 = st.columns(3)
    with exec_col_1:
        commission_per_lot = st.number_input(
            "Commission / lot",
            min_value=0.0,
            value=float(st.session_state.get(f"run_commission_{selected}_{run_symbol}", default_execution["commission_per_lot"])),
            step=0.1,
            key=f"run_commission_{selected}_{run_symbol}",
        )
    with exec_col_2:
        spread_pips = st.number_input(
            "Fallback spread",
            min_value=0.0,
            value=float(st.session_state.get(f"run_spread_{selected}_{run_symbol}", default_execution["spread_pips"])),
            step=0.01,
            key=f"run_spread_{selected}_{run_symbol}",
        )
    with exec_col_3:
        slippage_pips = st.number_input(
            "Slippage",
            min_value=0.0,
            value=float(st.session_state.get(f"run_slippage_{selected}_{run_symbol}", default_execution["slippage_pips"])),
            step=0.01,
            key=f"run_slippage_{selected}_{run_symbol}",
        )
    exec_col_4, exec_col_5, exec_col_6 = st.columns(3)
    with exec_col_4:
        tick_size = st.number_input(
            "Tick size",
            min_value=0.00001,
            value=float(st.session_state.get(f"run_tick_size_{selected}_{run_symbol}", default_execution.get("tick_size", 1.0))),
            step=0.01,
            format="%.5f",
            key=f"run_tick_size_{selected}_{run_symbol}",
        )
    with exec_col_5:
        latency_ms = st.number_input(
            "Latency (ms)",
            min_value=0,
            value=0,
            step=50,
            help="Simulates execution delay. Adds a volatility-based price penalty.",
            key=f"run_latency_{selected}",
        )
    with exec_col_6:
        slip_model = st.selectbox(
            "Slippage Model",
            ["Fixed", "Random (Exponential)"],
            index=0,
            key=f"run_slip_model_{selected}",
        )

    use_bar_spread = st.checkbox(
        "Use MT5 spread column",
        value=bool(st.session_state.get(f"run_bar_spread_{selected}_{run_symbol}", default_execution.get("use_bar_spread", False))),
        key=f"run_bar_spread_{selected}_{run_symbol}",
        help="When enabled, the backtester converts MT5 <SPREAD> values into price spread using the configured tick size.",
    )
    if st.button("Run backtest", type="primary", use_container_width=True, key=f"run_bt_{selected}"):
        with st.spinner("Running generated strategy on local data..."):
            try:
                strat_cls = _load_generated_strategy_class(ea)
                execution_config = {
                    "commission_per_lot": float(commission_per_lot),
                    "spread_pips": float(spread_pips),
                    "slippage_pips": float(slippage_pips),
                    "tick_size": float(tick_size),
                    "use_bar_spread": bool(use_bar_spread),
                    "execution_latency_ms": int(latency_ms),
                    "slippage_model": slip_model.split()[0].lower(),
                }
                result = run_backtest(
                    strat_cls,
                    symbol=run_symbol,
                    timeframe=ea["timeframe"],
                    date_from=str(date_from),
                    date_to=str(date_to),
                    overrides=ea.get("params", {}),
                    intrabar_steps=60 if intrabar else 1,
                    execution_config=execution_config,
                )
                st.session_state.setdefault("backtest_results", {})[selected] = backtest_result_payload(result)
                st.session_state["eas"][selected]["last_backtest_symbol"] = run_symbol
                st.session_state["eas"][selected]["last_execution_config"] = execution_config
                autosave()
                st.success(
                    f"Backtest finished: {result.n_trades} trades, net profit ${result.net_profit:,.0f}, "
                    f"Sharpe {result.sharpe_ratio:.2f}",
                    icon="✅",
                )
            except Exception as exc:
                st.error(f"Backtest failed: {exc}")

    with st.expander("Generated local engine strategy", expanded=False):
        st.code(engine_source or "# No generated engine strategy found", language="python")

    with st.expander("Generated Python review scaffold / payload", expanded=False):
        st.code(review_source or "# No generated review scaffold or payload found", language="python")

    filename = f"{ea['name']}.py"
    col_save, col_download = st.columns(2)
    with col_save:
        if st.button("Save review scaffold", type="secondary", use_container_width=True):
            GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            output_path = GENERATED_DIR / filename
            output_path.write_text(review_source, encoding="utf-8")
            st.session_state["eas"][selected]["review_path"] = str(output_path)
            autosave()
            st.success(f"Saved `{output_path}`", icon="✅")

    with col_download:
        st.download_button(
            "Download review scaffold",
            data=review_source.encode("utf-8"),
            file_name=filename,
            mime="text/x-python",
            use_container_width=True,
        )

    if ea.get("origin") == "python_template":
        st.markdown("##### Template payload")
        st.text_area(
            "Template payload JSON",
            value=ea.get("review_source", ""),
            height=220,
            disabled=True,
        )
    else:
        st.markdown("##### Source mapping")
        st.text_area(
            "Original MQL5 source",
            value=ea.get("source", ""),
            height=220,
            disabled=True,
        )


def _load_generated_strategy_class(ea: dict):
    root = Path(__file__).resolve().parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if ea.get("origin") == "python_template":
        if "strategy_module" in ea and ea["strategy_module"]:
            module_name = ea["strategy_module"]
            mod = importlib.reload(sys.modules[module_name]) if module_name in sys.modules else importlib.import_module(module_name)
            return getattr(mod, ea["strategy_class"])
        else:
            # Dynamically compile the spec from JSON if strategy_path is provided
            import json
            from services.python_strategy_service import strategy_spec_from_dict
            from services.native_lab.runtime import compile_runtime_strategy
            
            with open(ea["strategy_path"], "r") as f:
                payload = json.load(f)
            
            spec = strategy_spec_from_dict(payload)
            # Patch the params with any UI overrides
            if "params" in ea and ea["params"]:
                for k, v in ea["params"].items():
                    spec.params[k] = v
                    
            return compile_runtime_strategy(spec, ea.get("id", "runtime"))

    normalized_symbol = normalize_symbol(ea["symbol"])
    ea["symbol"] = normalized_symbol
    refreshed = convert_ea_source(
        source=ea["source"],
        strategy_name=ea["name"],
        symbol=normalized_symbol,
        timeframe=ea["timeframe"],
        ea_id=ea["id"],
    )
    paths = persist_converted_ea(refreshed, ea["name"])
    ea["params"] = refreshed.params
    ea["review_source"] = refreshed.review_source
    ea["engine_source"] = refreshed.engine_source
    ea["strategy_path"] = paths["engine_path"]
    ea["review_path"] = paths["review_path"]
    ea["strategy_module"] = refreshed.strategy_module
    ea["strategy_class"] = refreshed.strategy_class
    ea["conversion_warnings"] = refreshed.warnings
    ea["conversion_functions"] = refreshed.functions

    module_name = ea["strategy_module"]
    mod = importlib.reload(sys.modules[module_name]) if module_name in sys.modules else importlib.import_module(module_name)
    return getattr(mod, ea["strategy_class"])
