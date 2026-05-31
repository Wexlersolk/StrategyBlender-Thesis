from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ui.components.common import empty_state


def render_individual_results(eas: dict, results: dict):
    if not results:
        empty_state(
            "No backtest results yet. Convert/export a strategy first, then run your backtest pipeline.",
            "📊",
        )
        return

    ea_options = {
        ea_id: f"{eas[ea_id]['name']} — {eas[ea_id]['symbol']}"
        for ea_id in results if ea_id in eas
    }
    if not ea_options:
        empty_state("No matching EAs found.", "📊")
        return

    selected = st.selectbox(
        "Select strategy",
        list(ea_options.keys()),
        format_func=lambda x: ea_options[x],
    )
    result = results[selected]
    summary = result["summary"]
    monthly = result["monthly_df"].copy()
    balance_curve = result.get("balance_curve_df", pd.DataFrame()).copy()
    
    if "total_profit" not in monthly.columns and "profit" in monthly.columns:
        monthly["total_profit"] = monthly["profit"]
    if "num_trades" not in monthly.columns and "trades" in monthly.columns:
        monthly["num_trades"] = monthly["trades"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Profit", f"${summary['total_profit']:,.0f}")
    c2.metric("Sharpe (Daily)", f"{summary.get('sharpe_ratio_daily', 0):.2f}")
    c3.metric("Sharpe (Monthly)", f"{summary['sharpe_mean']:.2f}")
    c4.metric("Avg Win Rate", f"{summary['win_rate'] * 100:.1f}%")
    c5.metric("Total Trades", str(summary["num_trades"]))

    c_dd_1, c_dd_2 = st.columns(2)
    c_dd_1.metric(
        "Balance Drawdown Maximal",
        f"${summary.get('balance_dd_abs', 0):,.0f}",
        delta=f"{summary.get('balance_dd_pct', 0):.2f}%",
        delta_color="inverse",
    )
    c_dd_2.metric(
        "Equity Drawdown Maximal",
        f"${summary.get('equity_dd_abs', 0):,.0f}",
        delta=f"{summary.get('equity_dd_pct', 0):.2f}%",
        delta_color="inverse",
    )

    st.markdown("---")
    st.markdown("##### Balance Graph")
    if balance_curve.empty:
        st.info("No balance curve is available for this run.", icon="ℹ️")
    else:
        if not isinstance(balance_curve.index, pd.DatetimeIndex):
            balance_curve.index = pd.to_datetime(balance_curve.index, errors="coerce")
        balance_curve = balance_curve[balance_curve.index.notna()].sort_index()

        if len(balance_curve) == 1:
            start_time = pd.Timestamp(summary.get("date_from")) if summary.get("date_from") else balance_curve.index[0]
            if pd.notna(start_time):
                balance_curve.loc[start_time] = float(balance_curve["balance"].iloc[0])
                balance_curve = balance_curve.sort_index()

        fig_balance = go.Figure()
        fig_balance.add_trace(go.Scatter(
            x=balance_curve.index,
            y=balance_curve["balance"],
            mode="lines",
            name="Balance",
            line=dict(color="#2ECC71", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(46, 204, 113, 0.12)",
            hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Balance: $%{y:,.2f}<extra></extra>",
        ))
        fig_balance.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
            hovermode="x unified",
            font=dict(family="Inter, -apple-system, monospace", size=10),
        )
        fig_balance.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        fig_balance.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        st.plotly_chart(fig_balance, use_container_width=True)

        c_curve_1, c_curve_2, c_curve_3 = st.columns(3)
        c_curve_1.metric("Start Balance", f"${float(balance_curve['balance'].iloc[0]):,.0f}")
        c_curve_2.metric("End Balance", f"${float(balance_curve['balance'].iloc[-1]):,.0f}")
        c_curve_3.metric("Net Change", f"${float(balance_curve['balance'].iloc[-1] - balance_curve['balance'].iloc[0]):,.0f}")

    # ── Advanced Quant Metrics ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Quant Teardown & Factor Analysis")
    
    col_adv_1, col_adv_2, col_adv_3 = st.columns(3)
    col_adv_1.metric(
        f"Beta (vs {result.get('benchmark_symbol', 'US500')})", 
        f"{result.get('beta', 0):.2f}",
        help="Beta > 1 means strategy is more volatile than the benchmark. Beta < 0 means inverse correlation."
    )
    col_adv_2.metric(
        "Max Recovery Time", 
        f"{summary.get('max_recovery_days', 0)} days",
        help="The longest time (in days) the strategy took to reach a new equity high after a drawdown."
    )
    col_adv_3.metric(
        "Equity Stability", 
        f"{summary.get('equity_stability', 0):.2f}",
        help="Measure of consistency in returns. 1.0 is perfectly stable, lower values indicate high variance or unprofitable years."
    )

    # Underwater Plot
    underwater = result.get("underwater")
    if underwater is not None and not underwater.empty:
        if not isinstance(underwater.index, pd.DatetimeIndex):
            underwater.index = pd.to_datetime(underwater.index, errors="coerce")
        underwater = underwater[underwater.index.notna()].sort_index()
        
        fig_uw = go.Figure()
        fig_uw.add_trace(go.Scatter(
            x=underwater.index,
            y=underwater * 100,
            mode="lines",
            name="Underwater",
            line=dict(color="#E74C3C", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(231, 76, 60, 0.15)",
            hovertemplate="%{x|%Y-%m-%d}<br>Drawdown: %{y:.2f}%<extra></extra>",
        ))
        fig_uw.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=200,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
            font=dict(family="Inter, -apple-system, monospace", size=10),
        )
        fig_uw.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        fig_uw.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        st.plotly_chart(fig_uw, use_container_width=True)

    # Rolling Sharpe Plot
    rolling_sharpe = result.get("rolling_sharpe")
    if rolling_sharpe is not None and not rolling_sharpe.empty:
        if not isinstance(rolling_sharpe.index, pd.DatetimeIndex):
            rolling_sharpe.index = pd.to_datetime(rolling_sharpe.index, errors="coerce")
        rolling_sharpe = rolling_sharpe[rolling_sharpe.index.notna()].sort_index()
        
        # Filter out NaNs for plotting
        plot_sharpe = rolling_sharpe.dropna()
        if not plot_sharpe.empty:
            fig_rs = go.Figure()
            fig_rs.add_trace(go.Scatter(
                x=plot_sharpe.index,
                y=plot_sharpe,
                mode="lines",
                name="Rolling Sharpe (6m)",
                line=dict(color="#F1C40F", width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>Rolling Sharpe: %{y:.2f}<extra></extra>",
            ))
            fig_rs.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=200,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                xaxis_title=None,
                yaxis_title=None,
                font=dict(family="Inter, -apple-system, monospace", size=10),
            )
            fig_rs.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
            fig_rs.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
            st.plotly_chart(fig_rs, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Monthly Sharpe Ratio")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly.index,
        y=monthly["sharpe"],
        marker_color=["#2ECC71" if v > 0 else "#E74C3C" for v in monthly["sharpe"]],
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        font=dict(family="Inter, -apple-system, monospace", size=10),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Monthly Profit")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=monthly.index,
        y=monthly["total_profit"],
        marker_color=["#2E75B6" if v > 0 else "#C0392B" for v in monthly["total_profit"]],
    ))
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        font=dict(family="Inter, -apple-system, monospace", size=10),
    )
    fig2.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    fig2.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Monthly data table"):
        st.dataframe(monthly, use_container_width=True)


def render_portfolio_analysis(eas: dict, results: dict):
    from engine.portfolio import PortfolioEngine
    
    st.markdown("##### Portfolio Composition & Optimization")
    
    selected_ids = st.multiselect(
        "Select strategies for portfolio optimization",
        options=list(results.keys()),
        default=list(results.keys()),
        format_func=lambda x: f"{eas[x]['name']} — {eas[x]['symbol']}" if x in eas else x
    )
    
    if len(selected_ids) < 2:
        st.warning("Please select at least 2 strategies.")
        return

    # Extract returns
    returns_list = []
    used_names = set()
    for eid in selected_ids:
        res = results[eid]
        curve = res.get("balance_curve_df")
        if curve is not None and not curve.empty:
            if not isinstance(curve.index, pd.DatetimeIndex):
                curve.index = pd.to_datetime(curve.index)
            
            daily = curve["balance"].resample("B").last().ffill()
            rets = daily.pct_change().dropna()
            
            ea_meta = eas.get(eid, {})
            base_name = ea_meta.get("name") or eid
            name = _unique_series_name(base_name, used_names)
            rets.name = name
            returns_list.append(rets)
            
    if not returns_list:
        st.error("No valid returns data found for selected strategies.")
        return
        
    returns_df = pd.concat(returns_list, axis=1).dropna()
    
    if returns_df.empty:
        st.error("Strategies have non-overlapping date ranges or insufficient data.")
        return

    # Optimization Controls
    opt_col1, opt_col2 = st.columns([1, 2])
    with opt_col1:
        method = st.selectbox(
            "Optimization Method",
            ["Equal Weight", "Risk Parity (Inv Vol)", "Mean-Variance"],
            index=1
        )
        method_key = {
            "Equal Weight": "equal",
            "Risk Parity (Inv Vol)": "risk_parity",
            "Mean-Variance": "mean_variance"
        }[method]
        
        opt_results = PortfolioEngine.optimize(returns_df, method=method_key)
        weights = opt_results["weights"]
        
        st.markdown("**Optimal Weights**")
        w_df = pd.DataFrame([{"Strategy": k, "Weight": f"{v*100:.1f}%"} for k, v in weights.items()])
        st.dataframe(w_df, use_container_width=True, hide_index=True)

    with opt_col2:
        st.markdown("**Correlation Matrix**")
        corr = opt_results["correlation_matrix"]
        
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
            hoverongaps=False,
        ))
        fig_corr.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            font=dict(family="Inter, -apple-system, monospace", size=10),
        )
        fig_corr.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        fig_corr.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
        st.plotly_chart(fig_corr, use_container_width=True)

    # ── Performance Comparison ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"##### Optimized Portfolio Performance ({method})")
    
    portfolio_rets = opt_results["portfolio_returns"]
    portfolio_equity = 100_000 * (1 + portfolio_rets).cumprod()
    
    ew_rets = (returns_df * (1.0/len(selected_ids))).sum(axis=1)
    ew_equity = 100_000 * (1 + ew_rets).cumprod()

    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(
        x=portfolio_equity.index,
        y=portfolio_equity,
        mode="lines",
        name=f"Optimized ({method})",
        line=dict(color="#2ECC71", width=3),
    ))
    fig_comp.add_trace(go.Scatter(
        x=ew_equity.index,
        y=ew_equity,
        mode="lines",
        name="Equal Weight (Baseline)",
        line=dict(color="#8B9BB4", width=1.5, dash='dot'),
    ))
    fig_comp.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        font=dict(family="Inter, -apple-system, monospace", size=10),
    )
    fig_comp.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    fig_comp.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    st.plotly_chart(fig_comp, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    
    def calc_metrics(rets):
        sharpe = (rets.mean() / (rets.std() + 1e-9)) * np.sqrt(252)
        cum_ret = (1 + rets).prod() - 1
        equity = (1 + rets).cumprod()
        peak = equity.cummax()
        dd = (equity - peak) / peak
        max_dd = dd.min()
        return sharpe, cum_ret, max_dd

    opt_s, opt_r, opt_d = calc_metrics(portfolio_rets)
    ew_s, ew_r, ew_d = calc_metrics(ew_rets)

    c1.metric("Portfolio Sharpe", f"{opt_s:.2f}", delta=f"{opt_s - ew_s:.2f}")
    c2.metric("Max Drawdown", f"{opt_d*100:.2f}%", delta=f"{(opt_d - ew_d)*100:.2f}%", delta_color="inverse")
    c3.metric("Total Return", f"{opt_r*100:.1f}%", delta=f"{(opt_r - ew_r)*100:.1f}%")
    c4.metric("Avg Correlation", f"{corr.values[np.triu_indices_from(corr.values, k=1)].mean():.2f}")

    st.markdown("##### Individual Strategy Equity Curves (Scaled)")
    
    fig_ind = go.Figure()
    for col in returns_df.columns:
        weight = weights.get(col, 1.0/len(selected_ids))
        ind_equity = 100_000 * (1 + returns_df[col] * weight).cumprod()
        fig_ind.add_trace(go.Scatter(
            x=ind_equity.index,
            y=ind_equity,
            mode="lines",
            name=col,
            line=dict(width=1),
            opacity=0.6,
        ))
    
    fig_ind.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, -apple-system, monospace", size=10),
    )
    fig_ind.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    fig_ind.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False, tickfont=dict(size=10, color="#8B9BB4"))
    st.plotly_chart(fig_ind, use_container_width=True)


def _unique_series_name(base: str, used: set[str]) -> str:
    candidate = (base or "Strategy").strip()
    if candidate not in used:
        used.add(candidate)
        return candidate

    idx = 2
    while True:
        numbered = f"{candidate} ({idx})"
        if numbered not in used:
            used.add(numbered)
            return numbered
        idx += 1
