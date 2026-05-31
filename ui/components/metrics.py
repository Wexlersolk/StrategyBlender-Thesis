from __future__ import annotations

import pandas as pd
import streamlit as st
from research.trade_dataset import dataset_summary

def render_dataset_metrics(dataset: pd.DataFrame):
    """Renders high-level metrics for a trade dataset in Streamlit columns."""
    summary = dataset_summary(dataset)
    if not summary:
        return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Strategies", summary["strategies"])
    c2.metric("Decisions", f"{summary['decisions']:,}")
    c3.metric("Trade Rate", f"{summary['trade_rate'] * 100:.1f}%")
    c4.metric("Decision Win Rate", f"{summary['win_rate'] * 100:.1f}%")
    c5.metric("Avg Net Profit", f"${summary['avg_profit']:,.2f}")
