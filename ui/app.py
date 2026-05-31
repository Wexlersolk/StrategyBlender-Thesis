"""
ui/app.py — StrategyBlender main entry point

Run with:
    python -m streamlit run ui/app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from research import auth
from ui.state import init_state
from ui.profile_manager import (
    load_workspace_profile
)

st.set_page_config(
    page_title="StrategyBlender Quant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Ultra-Aggressive Bloomberg / Quant Terminal Theme */
    
    /* 1. Base Terminal Font & Colors */
    html, body, [data-testid="stAppViewContainer"], [class*="css"] {
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace !important;
        background-color: #05070A !important; /* Extremely dark blue-black */
        color: #8B9BB4 !important;
        font-size: 13px !important;
    }

    /* 2. Kill all Streamlit paddings */
    .main .block-container {
        padding: 0.5rem 1rem 1rem 1rem !important;
        max-width: 100% !important;
    }

    /* 3. Sidebar - rigid tool panel */
    [data-testid="stSidebar"] {
        background-color: #0A0D14 !important;
        border-right: 1px solid #1C212B !important;
        width: 240px !important;
    }
    [data-testid="stSidebar"] * {
        font-size: 12px !important;
    }

    /* 4. Widgets & Inputs - brutalist */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #020305 !important;
        border: 1px solid #1C212B !important;
        border-radius: 0px !important;
        color: #C9D1D9 !important;
        padding: 2px 6px !important;
        min-height: 28px !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }
    .stButton > button {
        background-color: #0E121A !important;
        border: 1px solid #1C212B !important;
        border-radius: 0px !important;
        color: #8B9BB4 !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        min-height: 28px !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        font-size: 11px !important;
    }
    .stButton > button:hover {
        background-color: #161B22 !important;
        border-color: #388BFD !important;
        color: #C9D1D9 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #102A4C !important;
        border: 1px solid #1F6FEB !important;
        color: #58A6FF !important;
    }

    /* 5. Tabs - IDE Style */
    [data-baseweb="tab-list"] {
        background-color: #020305 !important;
        border-bottom: 1px solid #1C212B !important;
        gap: 0px !important;
    }
    [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        border-right: 1px solid #1C212B !important;
        border-radius: 0px !important;
        color: #5E6E8A !important;
        padding: 6px 12px !important;
        font-weight: normal !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        background-color: #0A0D14 !important;
        color: #58A6FF !important;
        border-top: 2px solid #58A6FF !important;
        font-weight: bold !important;
    }

    /* 6. Metrics - HUD Style */
    [data-testid="stMetric"] {
        background-color: #0A0D14 !important;
        border: 1px solid #1C212B !important;
        padding: 6px 10px !important;
        border-radius: 0px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #5E6E8A !important;
        text-transform: uppercase !important;
        font-size: 10px !important;
        letter-spacing: 0.5px !important;
    }
    [data-testid="stMetricValue"] {
        color: #E6EDF3 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 11px !important;
    }

    /* 7. DataFrames / Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #1C212B !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }
    [data-testid="stDataFrame"] > div {
        background-color: #020305 !important;
    }

    /* 8. Expanders - Accordion */
    [data-testid="stExpander"] {
        background-color: #0A0D14 !important;
        border: 1px solid #1C212B !important;
        border-radius: 0px !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #0E121A !important;
        padding: 8px !important;
        color: #8B9BB4 !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        font-weight: bold !important;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #C9D1D9 !important;
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin-bottom: 0.5rem !important;
    }
    hr {
        border-color: #1C212B !important;
        margin: 1rem 0 !important;
    }
    
    /* Remove headers */
    header { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }
    #MainMenu { visibility: hidden !important; display: none !important; }

    /* Custom Scrollbar for Terminal look */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #05070A; }
    ::-webkit-scrollbar-thumb { background: #1C212B; border-radius: 0px; }
    ::-webkit-scrollbar-thumb:hover { background: #58A6FF; }

</style>
""", unsafe_allow_html=True)


def main():
    init_state()
    auth.bootstrap_default_admin()
    _bind_auth_context()
    if not st.session_state.get("auth_user_id"):
        with st.sidebar:
            _render_login()
        st.info("Sign in to access persisted research jobs and experiments.")
        return
    if not st.session_state.get("_workspace_loaded"):
        _load_workspace_state()
        st.session_state["_workspace_loaded"] = True

    with st.sidebar:
        _render_sidebar()

    _render_page()


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar():
    # Logo
    st.markdown("""
    <div style='padding:0.5rem 0 1rem 0;'>
        <h1 style='color:#58A6FF;font-size:1.1rem;margin:0;font-family: monospace;'>[ STRATEGY_BLENDER ]<br/><span style='color:#E6EDF3;'>:: QUANT_TERMINAL</span></h1>
        <p style='color:#5E6E8A;font-size:0.65rem;margin-top:4px;text-transform:uppercase;'>v4.0.0-rc2 | MT5-Bridge Active</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown(
        "<p style='color:#8B9BB4;font-size:0.75rem;letter-spacing:0.08em;"
        "text-transform:uppercase;margin:0 0 6px 0;'>Navigation</p>",
        unsafe_allow_html=True
    )

    pages = {
        "Dashboard": "📊",
        "EA Manager": "🤖",
        "Strategy Builder": "🧩",
        "Backtests": "▶️",
        "Quant Lab": "🏛️",
        "ML Lab": "🧠",
        "Experiments": "🧪",
        "Legacy Research": "🔬",
    }
    for page_name, icon in pages.items():
        is_active_page = st.session_state.get("page") == page_name
        if st.button(
            f"{icon}  {page_name}",
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if is_active_page else "secondary",
        ):
            st.session_state["page"] = page_name
            st.rerun()

    st.markdown("---")

    user_id = st.session_state.get("auth_user_id", "")
    st.caption(f"Signed in as `{user_id}`")
    if st.button("Sign Out", key="sign_out", use_container_width=True, type="secondary"):
        token = st.session_state.get("auth_session_token", "")
        auth.revoke_session(token)
        st.session_state["auth_user_id"] = ""
        st.session_state["auth_session_token"] = ""
        auth.bind_user(None)
        st.rerun()

    # ── Status summary ────────────────────────────────────────────────────────
    n_eas    = len(st.session_state.get("eas", {}))
    n_tested = len(st.session_state.get("backtest_results", {}))
    trained  = st.session_state.get("model_trained", False)

    st.markdown(f"""
    <div style='color:#8B9BB4;font-size:0.8rem;line-height:2;'>
        EAs loaded:&nbsp; <b style='color:#E8EDF3;'>{n_eas}</b><br>
        Backtested:&nbsp; <b style='color:#E8EDF3;'>{n_tested}</b><br>
        ML models:&nbsp; <b style='color:{"#2ECC71" if trained else "#E74C3C"};'>
            {"Ready ✅" if trained else "Not ready"}</b>
    </div>
    """, unsafe_allow_html=True)

def _load_workspace_state():
    profile = load_workspace_profile()
    if not profile:
        return
    st.session_state["eas"] = profile.get("eas", {})
    st.session_state["backtest_results"] = profile.get("backtest_results", {})
    st.session_state["ai_experiment_results"] = profile.get("ai_experiment_results", {})
    st.session_state["model_trained"] = profile.get("model_trained", False)
    st.session_state["training_log"] = profile.get("training_log", [])
    st.session_state["training_artifact"] = profile.get("training_artifact")
    st.session_state["_ai_dataset_id"] = profile.get("ai_dataset_id", "")
    st.session_state["_ai_training_artifact_id"] = profile.get("ai_training_artifact_id", "")
    st.session_state["schedule_path"] = profile.get("schedule_path", "")
    st.session_state["ai_saved_reports"] = profile.get("ai_saved_reports", [])
    st.session_state["_ai_model_wfo"] = profile.get("ai_model_wfo")
    st.session_state["_ai_model_wfo_run_id"] = profile.get("ai_model_wfo_run_id", "")
    st.session_state["experiment_registry"] = profile.get("experiment_registry", [])
    st.session_state["job_registry"] = profile.get("job_registry", [])
    if not st.session_state.get("auth_user_id"):
        st.session_state["auth_user_id"] = profile.get("auth_user_id", "")


def _bind_auth_context():
    token = st.session_state.get("auth_session_token", "")
    user_id = st.session_state.get("auth_user_id", "")
    if token:
        session = auth.resolve_session(token)
        if session:
            user_id = session["user_id"]
            st.session_state["auth_user_id"] = user_id
        else:
            st.session_state["auth_user_id"] = ""
            st.session_state["auth_session_token"] = ""
            user_id = ""
    auth.bind_user(user_id or None)


def _render_login():
    st.markdown("### Sign In")
    username = st.text_input("User ID", key="login_user_id")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Sign In", key="login_submit", use_container_width=True, type="primary"):
        session = auth.authenticate_user(user_id=username, password=password)
        if not session:
            st.error("Invalid credentials.")
            return
        st.session_state["auth_user_id"] = session["user_id"]
        st.session_state["auth_session_token"] = session["token"]
        auth.bind_user(session["user_id"])
        st.rerun()


# ── Page router ───────────────────────────────────────────────────────────────

def _render_page():
    page = st.session_state.get("page", "Dashboard")

    if page == "Dashboard":
        from ui.views.dashboard import render
        render()
    elif page == "EA Manager":
        from ui.views.ea_manager import render
        render()
    elif page == "Strategy Builder":
        from ui.views.strategy_builder import render
        render()
    elif page == "Backtests":
        from ui.views.backtests import render
        render()
    elif page == "Quant Lab":
        from ui.views.quant_lab import render
        render()
    elif page == "ML Lab":
        from ui.views.ai_training import render
        render()
    elif page == "Experiments":
        from ui.views.experiments import render
        render()
    elif page == "Legacy Research":
        from ui.views.research import render
        render()


if __name__ == "__main__":
    main()
