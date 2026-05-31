from __future__ import annotations

import pandas as pd
import plotly.express as px

def scatter_chart(df: pd.DataFrame, x_col: str, y_col: str, size_col: str, title: str):
    """Renders a Plotly scatter chart."""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        size=size_col,
        hover_name="name" if "name" in df.columns else None,
        hover_data=["strategy_id", "accepted", "score"] if all(c in df.columns for c in ["strategy_id", "accepted", "score"]) else None,
        color="accepted" if "accepted" in df.columns else None,
        title=title,
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def bar_rank_chart(df: pd.DataFrame):
    """Renders a Plotly bar chart for strategy ranking."""
    fig = px.bar(
        df,
        x="name" if "name" in df.columns else None,
        y="risk_adjusted" if "risk_adjusted" in df.columns else None,
        color="bucket" if "bucket" in df.columns else None,
        hover_data=["strategy_id", "score", "profit_factor", "drawdown_pct"] if all(c in df.columns for c in ["strategy_id", "score", "profit_factor", "drawdown_pct"]) else None,
        title="Top Candidates By Risk-Adjusted Rank",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), xaxis_title="")
    return fig
