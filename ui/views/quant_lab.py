from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine.data_loader import load_bars
from research.event_discovery import build_xauusd_event_hypotheses, discover_event_hypotheses
from research.hypothesis_testing import (
    analyze_trade_hypothesis,
    directional_trade_breakdown,
    yearly_trade_breakdown,
)
from services.backtest_service import available_backtest_symbols, discover_strategies, run_backtest
from ui.components.common import empty_state, error_box, section_header


def render():
    section_header(
        "Quant Lab",
        "Research alpha, validate hypotheses, and connect strategy generation to a professional quant workflow.",
    )

    tab_overview, tab_hypothesis, tab_events, tab_ml = st.tabs(
        [
            "🏛️ Research Stack",
            "🧪 Hypothesis Testing",
            "🔎 Event Discovery",
            "🤖 ML & Deployment",
        ]
    )

    with tab_overview:
        _render_overview_tab()
    with tab_hypothesis:
        _render_hypothesis_tab()
    with tab_events:
        _render_event_tab()
    with tab_ml:
        _render_ml_tab()


def _render_overview_tab():
    st.markdown("#### Platform framing")
    st.caption(
        "The app is no longer positioned as a light AI add-on. The research stack now centers on "
        "strategy generation, statistical validation, robustness testing, and deployable execution logic."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Strategies Loaded", len(st.session_state.get("eas", {})))
    col2.metric("Backtests Cached", len(st.session_state.get("backtest_results", {})))
    col3.metric("Saved Experiments", len(st.session_state.get("experiment_registry", [])))
    col4.metric("Dataset Ready", "Yes" if st.session_state.get("_ai_dataset_id") else "No")

    stack = pd.DataFrame(
        [
            {"Layer": "Research design", "Method": "Hypothesis testing", "Status": "Implemented", "Notes": "t-test, sign test, bootstrap CI, permutation test, yearly and directional splits"},
            {"Layer": "Robustness", "Method": "Walk-forward + Monte Carlo", "Status": "Implemented", "Notes": "Existing research engine and legacy research page"},
            {"Layer": "Alpha discovery", "Method": "Event hypothesis mining", "Status": "Implemented", "Notes": "XAUUSD structural event discovery with regime and session filters"},
            {"Layer": "Execution overlays", "Method": "Vol target / drawdown throttle", "Status": "Implemented", "Notes": "Deterministic controls before ML"},
            {"Layer": "ML overlays", "Method": "Meta-filter + sizing models", "Status": "Implemented", "Notes": "Decision-level dataset, filter probabilities, dynamic sizing"},
            {"Layer": "Deployment", "Method": "Python to MT5 workflow", "Status": "Available", "Notes": "Strategy generation, conversion, export, and MT5 backtest scripts already exist in repo"},
        ]
    )
    st.dataframe(stack, use_container_width=True, hide_index=True)

    st.markdown("#### Operating model")
    st.markdown(
        "1. Generate or import a strategy.\n"
        "2. Validate baseline performance and robustness.\n"
        "3. Test the return hypothesis, not just the backtest headline.\n"
        "4. Mine event structures or build decision datasets.\n"
        "5. Add deterministic overlays, then ML overlays, then export to MT5."
    )


def _render_hypothesis_tab():
    st.markdown("#### Alpha hypothesis validation")
    st.caption(
        "This tests whether a strategy's trade expectancy is statistically distinguishable from zero. "
        "Use it to reject weak backtests before spending time on optimization or MT5 deployment."
    )

    strategies = discover_strategies()
    if not strategies:
        empty_state("No Python strategies found in `strategies/`.", "🧪")
        return

    symbols = available_backtest_symbols("H1")
    if not symbols:
        empty_state("No market data found in `data/exports/MT5 data export`.", "📉")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        strategy_name = st.selectbox("Strategy", list(strategies.keys()), key="quant_hypothesis_strategy")
    with col2:
        symbol = st.selectbox("Symbol", symbols, key="quant_hypothesis_symbol")
    with col3:
        intrabar = st.checkbox("Use M1 intrabar", value=symbol.upper() == "XAUUSD", key="quant_hypothesis_intrabar")

    col4, col5, col6 = st.columns(3)
    with col4:
        date_from = st.date_input("From", value=pd.Timestamp("2020-01-01"), key="quant_hypothesis_from")
    with col5:
        date_to = st.date_input("To", value=pd.Timestamp("2025-12-31"), key="quant_hypothesis_to")
    with col6:
        null_mean = st.number_input("Null mean / trade", value=0.0, step=1.0, key="quant_hypothesis_null")

    if st.button("Run Hypothesis Test", type="primary", use_container_width=True, key="quant_hypothesis_run"):
        with st.spinner("Running backtest and statistical validation..."):
            try:
                result = run_backtest(
                    strategies[strategy_name],
                    symbol=symbol,
                    timeframe="H1",
                    date_from=str(date_from),
                    date_to=str(date_to),
                    intrabar_steps=60 if intrabar else 1,
                )
                report = analyze_trade_hypothesis(result, null_mean=float(null_mean))
                st.session_state["_quant_hypothesis_result"] = result
                st.session_state["_quant_hypothesis_report"] = report
            except Exception as exc:
                error_box(f"Hypothesis test failed: {exc}")

    result = st.session_state.get("_quant_hypothesis_result")
    report = st.session_state.get("_quant_hypothesis_report")
    if not result or not report:
        st.info("Run a hypothesis test to populate the diagnostics.", icon="ℹ️")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trades", report.sample_size)
    c2.metric("Mean / Trade", f"${report.mean_profit:,.2f}")
    c3.metric("95% CI", f"${report.bootstrap_mean_ci_low:,.2f} to ${report.bootstrap_mean_ci_high:,.2f}")
    c4.metric("Positive p-value", f"{report.t_pvalue_positive:.4f}")
    c5.metric("Hypothesis", "Accepted" if report.rejects_null_positive else "Not proven")

    stats_table = pd.DataFrame(
        [
            {"Metric": "Hit rate", "Value": f"{report.hit_rate * 100:.1f}%"},
            {"Metric": "Positive month rate", "Value": f"{report.positive_month_rate * 100:.1f}%"},
            {"Metric": "t-statistic", "Value": f"{report.t_statistic:.3f}"},
            {"Metric": "Sign-test p-value", "Value": f"{report.sign_pvalue_two_sided:.4f}"},
            {"Metric": "Permutation p-value", "Value": f"{report.permutation_pvalue_positive:.4f}"},
            {"Metric": "Effect size", "Value": f"{report.effect_size:.3f}"},
            {"Metric": "Total profit", "Value": f"${report.total_profit:,.2f}"},
        ]
    )
    st.dataframe(stats_table, use_container_width=True, hide_index=True)

    st.markdown("#### Trade distribution")
    profits = pd.Series(result.profits, dtype=float)
    fig = px.histogram(
        x=profits,
        nbins=40,
        color_discrete_sequence=["#2E75B6"],
        labels={"x": "Net profit per trade ($)"},
    )
    fig.add_vline(x=float(report.null_mean), line_color="#E74C3C", line_dash="dash")
    fig.add_vrect(
        x0=report.bootstrap_mean_ci_low,
        x1=report.bootstrap_mean_ci_high,
        fillcolor="rgba(46,117,182,0.15)",
        line_width=0,
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    c6, c7 = st.columns(2)
    with c6:
        st.markdown("#### Yearly stability")
        st.dataframe(yearly_trade_breakdown(result), use_container_width=True, hide_index=True)
    with c7:
        st.markdown("#### Directional split")
        st.dataframe(directional_trade_breakdown(result), use_container_width=True, hide_index=True)


def _render_event_tab():
    st.markdown("#### Event-driven alpha discovery")
    st.caption(
        "This mines structural event hypotheses rather than optimizing entry parameters blindly. "
        "The current implementation focuses on XAUUSD because that is where the event library is strongest."
    )

    try:
        available = available_backtest_symbols("H1")
    except Exception:
        available = []
    if "XAUUSD" not in {item.upper(): item for item in available}:
        st.info("XAUUSD H1 data is required for the current event discovery workflow.", icon="ℹ️")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        date_from = st.date_input("Discovery from", value=pd.Timestamp("2020-01-01"), key="quant_event_from")
    with col2:
        date_to = st.date_input("Discovery to", value=pd.Timestamp("2025-12-31"), key="quant_event_to")
    with col3:
        top_n = st.slider("Top hypotheses", min_value=5, max_value=30, value=12, step=1, key="quant_event_topn")

    col4, col5 = st.columns(2)
    with col4:
        min_signals = st.slider("Minimum signals", min_value=10, max_value=80, value=25, step=5, key="quant_event_minsignals")
    with col5:
        timeframe = st.selectbox("Timeframe", ["H1"], key="quant_event_timeframe")

    if st.button("Run Event Discovery", type="primary", use_container_width=True, key="quant_event_run"):
        with st.spinner("Scanning XAUUSD event hypotheses..."):
            try:
                df = load_bars("XAUUSD", timeframe, date_from=str(date_from), date_to=str(date_to))
                hypotheses = build_xauusd_event_hypotheses(timeframe=timeframe)
                results = discover_event_hypotheses(df, hypotheses, top_n=int(top_n), min_signals=int(min_signals))
                st.session_state["_quant_event_results"] = results
            except Exception as exc:
                error_box(f"Event discovery failed: {exc}")

    results = st.session_state.get("_quant_event_results", [])
    if not results:
        st.info("Run event discovery to rank structural hypotheses.", icon="ℹ️")
        return

    table = pd.DataFrame(
        [
            {
                "Hypothesis": item.hypothesis.label,
                "Family": item.hypothesis.family,
                "Side": item.hypothesis.side,
                "Regime": item.hypothesis.regime,
                "Session": item.hypothesis.session,
                "Signals": item.signal_count,
                "Avg Return": item.avg_return,
                "Win Rate": item.win_rate,
                "Fitness": item.fitness_score,
                "Novelty": item.novelty_score,
                "Total Score": item.total_score,
            }
            for item in results
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=table["Signals"],
            y=table["Total Score"],
            mode="markers+text",
            text=table["Family"],
            textposition="top center",
            marker=dict(
                size=(table["Win Rate"] * 30).clip(lower=8),
                color=table["Avg Return"],
                colorscale="RdYlGn",
                showscale=True,
                colorbar=dict(title="Avg return"),
            ),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Signal count",
        yaxis_title="Total score",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_ml_tab():
    st.markdown("#### ML overlays and MT5 deployment path")
    st.caption(
        "The existing ML pipeline is decision-level rather than price-prediction theater. "
        "It learns whether to allow a trade and how to size it after the base strategy emits a signal."
    )

    methods = pd.DataFrame(
        [
            {"Component": "Filter model", "Implementation": "Regularized logistic meta-filter", "Purpose": "Block lower-quality trade decisions"},
            {"Component": "Sizing model", "Implementation": "Ridge-style linear sizing model", "Purpose": "Scale exposure by expected trade quality"},
            {"Component": "Benchmark overlays", "Implementation": "Vol target and drawdown throttle", "Purpose": "Compare ML against deterministic risk controls"},
            {"Component": "Validation", "Implementation": "Walk-forward overlay evaluation", "Purpose": "Test out-of-sample behavior across splits"},
            {"Component": "Export path", "Implementation": "Strategy conversion + MT5 scripts", "Purpose": "Move researched logic into MT5-native testing"},
        ]
    )
    st.dataframe(methods, use_container_width=True, hide_index=True)

    st.markdown("#### Recommended workflow")
    st.markdown(
        "1. Build the trade dataset in `ML Lab`.\n"
        "2. Benchmark deterministic overlays before enabling ML.\n"
        "3. Train filter and sizing models only on decision features.\n"
        "4. Validate via walk-forward overlay evaluation.\n"
        "5. Export the surviving logic into the MT5 workflow."
    )

    st.info(
        "Use the `ML Lab` page for the full dataset, overlay benchmark, and model training workflow. "
        "Use `Legacy Research` when you want the older single-strategy backtest/WFO/Monte Carlo UI.",
        icon="ℹ️",
    )
