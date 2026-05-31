from __future__ import annotations

import pandas as pd
import streamlit as st
from research.state_store import list_jobs
from ui.job_runner import cancel_background_job, job_audit_log

def render_strategy_builder_jobs():
    """Renders the background research jobs section for Strategy Builder."""
    jobs = [job for job in list_jobs() if job.get("kind") in {"native_batch_generation", "native_batch_retest", "native_generator"}]
    if not jobs:
        return
    st.markdown("##### Background Research Jobs")
    listing = pd.DataFrame(jobs)[["job_id", "title", "status", "stage", "progress_pct", "submitted_at", "result_run_id"]]
    st.dataframe(listing, use_container_width=True, hide_index=True)
    selected_job_id = st.selectbox(
        "Batch Job Details",
        [job["job_id"] for job in jobs],
        format_func=lambda value: next((f"{item['title']} | {item['status']} | {value}" for item in jobs if item["job_id"] == value), value),
        key="strategy_builder_job_select",
    )
    selected_job = next(job for job in jobs if job["job_id"] == selected_job_id)
    progress = float(selected_job.get("progress_pct", 0.0))
    st.progress(min(max(progress / 100.0, 0.0), 1.0), text=f"{selected_job.get('stage', '')} ({progress:.0f}%)")
    if selected_job.get("status") in {"queued", "running"}:
        if st.button("Stop Selected Job", use_container_width=True, key=f"cancel_job_{selected_job_id}"):
            cancel_background_job(selected_job_id)
            st.rerun()
    if selected_job.get("result_run_id"):
        st.caption(f"Completed run: {selected_job['result_run_id']}")
    events = pd.DataFrame(list(selected_job.get("events", [])))
    if not events.empty:
        st.dataframe(events.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
    audit = pd.DataFrame(job_audit_log(selected_job_id, limit=25))
    if not audit.empty:
        with st.expander("Job Audit Trail", expanded=False):
            st.dataframe(audit, use_container_width=True, hide_index=True)
