from __future__ import annotations

import pandas as pd
import streamlit as st
from research.experiment_registry import list_experiment_records

def render_experiment_registry():
    """Renders the experiment registry table."""
    registry = list_experiment_records()
    if not registry:
        return
    st.markdown("#### Experiment Registry")
    st.dataframe(pd.DataFrame(registry), use_container_width=True, hide_index=True)
