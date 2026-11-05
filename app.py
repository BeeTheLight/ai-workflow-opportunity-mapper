"""AI Workflow Opportunity Mapper — Streamlit app.

LLM finds and explains · code calculates · a human approves.
Run locally:  streamlit run app.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from mapper.ingest import load_sources
from mapper.llm import DEFAULT_MODEL, analyze, load_cached
from mapper.roadmap import DISCLAIMER, build_markdown
from mapper.roi import Assumptions, compute
from mapper.validate import validate

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DEMO_CACHE = ROOT / "sample_output" / "demo_analysis.json"
DECISIONS = ["Pending", "Approved", "Needs more info", "Rejected"]
COMPANY_CONTEXT = (
    "Kestrel Pay (fictional) is a cross-border payments company serving merchants in Nigeria, "
    "Kenya, Ghana, South Africa, the US and UK. Regulated via a sponsor bank; has an MLRO. "
    "About 45 operations staff across support, onboarding and compliance."
)

st.set_page_config(page_title="AI Workflow Opportunity Mapper", page_icon="🧭", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1250px;}
  .estimate {background:#FFF7E6; border-left:4px solid #D98E04; padding:.6rem .9rem; border-radius:4px; color:#4A3500;}
  .pill {display:inline-block; padding:2px 8px; border-radius:10px; font-size:.78rem; margin-right:4px;
         background:#E8EEF7; color:#1F3A5F;}
  .src {font-family: ui-monospace, monospace; font-size:.8rem; color:#1F3A5F;}
</style>""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- state
def _init():
    for k, v in {"bundle": None, "analysis": None, "validation": None, "review": None,
                 "load_error": None}.items():
        st.session_state.setdefault(k, v)


_init()


def sample_files() -> list[tuple[str, bytes]]:
    return [(p.name, p.read_bytes()) for p in sorted(DATA_DIR.iterdir()) if p.suffix in {".csv", ".md"}]


def reset_downstream():
    st.session_state.analysis = st.session_state.validation = st.session_state.review = None


def seed_review(analysis: dict) -> pd.DataFrame:
    rows = []
    for o in analysis["opportunities"]:
        rows.append({
            "id": o["id"], "title": o["title"], "decision": "Pending",
            "automatable_share": o["suggested_automatable_share"],
            "review_overhead": o["suggested_review_overhead"],
            "complexity": o["complexity"], "feasibility": o["feasibility"], "risk": o["risk"],
            "reviewer_note": "",
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    try:
        secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:  # no secrets.toml present
        secret_key = ""
    if secret_key and not os.getenv("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = secret_key
    has_env_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    mode = st.radio("Analysis mode", ["Demo (no API key)", "Live (Claude API)"],
                    help="Demo replays a saved analysis of the sample data. Live sends your uploads to Claude.")
    api_key = None
    if mode.startswith("Live"):
        api_key = st.text_input("Anthropic API key", type="password",
                                help="Used for this session only. Not stored.") or None
        model = st.text_input("Model", value=DEFAULT_MODEL)
        if not (api_key or has_env_key):
            st.info("Add a key to run a live analysis.")
    else:
        model = DEFAULT_MODEL

    st.divider()
    st.subheader("Assumptions")
    st.caption("Every savings figure is computed from these. Change them and the numbers update.")
    a = Assumptions()
    a.loaded_hourly_cost = st.number_input("Loaded cost per ops hour (USD)", 5.0, 300.0, a.loaded_hourly_cost, 1.0)
    c1, c2 = st.columns(2)
    a.sample_multipliers = {
        "SUP": c1.number_input("Support sample ×", 1.0, 500.0, a.sample_multipliers["SUP"], 1.0,
                               help="Sample tickets × this = monthly volume (200 × 20 = 4,000/mo)"),
        "CMP": c2.number_input("Compliance sample ×", 1.0, 500.0, a.sample_multipliers["CMP"], 1.0,
                               help="150 sampled reviews × 10 = 1,500/mo"),
    }
    a.default_sample_multiplier = st.number_input("Other uploaded samples ×", 1.0, 500.0, 1.0, 1.0)
    a.weekly_build_cost = st.number_input("Build cost per week (USD)", 500.0, 50000.0, a.weekly_build_cost, 500.0)
    with st.expander("Prioritization weights"):
        a.weight_value = st.slider("Value", 0.0, 1.0, a.weight_value, 0.05)
        a.weight_feasibility = st.slider("Feasibility", 0.0, 1.0, a.weight_feasibility, 0.05)
        a.weight_risk = st.slider("Low risk", 0.0, 1.0, a.weight_risk, 0.05)
        a.risk_gate = st.slider("Risk gate → Phase 3 at risk ≥", 2, 5, a.risk_gate)

# ----------------------------------------------------------------------------- header
st.title("🧭 AI Workflow Opportunity Mapper")
st.markdown("Find which manual workflows to automate first. **Claude finds and explains the "
            "opportunities, deterministic code calculates the savings, and a human approves the plan.**")
st.markdown(f'<div class="estimate">⚠️ {DISCLAIMER}</div>', unsafe_allow_html=True)
st.write("")

t_in, t_ai, t_rev, t_roi, t_how = st.tabs(
    ["① Inputs", "② AI analysis", "③ Review & approve", "④ ROI & roadmap", "How it works"])

# ----------------------------------------------------------------------------- 1. inputs
with t_in:
    st.subheader("Business inputs")
    use_sample = st.toggle("Use sample data — Kestrel Pay, a fictional cross-border payments company", value=True)
    uploads = None
    if not use_sample:
        uploads = st.file_uploader("Upload process CSVs and interview notes / SOPs (.md, .txt)",
                                   type=["csv", "md", "txt"], accept_multiple_files=True)
        st.caption("CSVs need a task/category column and a minutes column. Add `monthly_volume` if rows "
                   "are process steps rather than individual cases.")
        if mode.startswith("Demo"):
            st.warning("Demo mode only replays the sample analysis. Switch to Live mode to analyze your own files.")

    if st.button("Load and profile data", type="primary"):
        files = sample_files() if use_sample else [(f.name, f.getvalue()) for f in (uploads or [])]
        try:
            st.session_state.bundle = load_sources(files)
            st.session_state.load_error = None
            st.session_state.is_sample = use_sample
            reset_downstream()
        except Exception as e:  # surface parsing problems to the user
            st.session_state.load_error = str(e)

    if st.session_state.load_error:
        st.error(st.session_state.load_error)

    b = st.session_state.bundle
    if b is not None:
        st.success(f"Loaded {len(b.sources)} files · {len(b.records)} records · "
                   f"{len(b.paragraphs)} document paragraphs · {len(b.tasks)} distinct tasks")
        for w in b.warnings:
            st.warning(w)
        st.markdown("**Task profile** — computed by code from your data. These are the only volumes "
                    "and handle times the savings model uses.")
        show = b.tasks[["task_key", "process", "task", "volume_basis", "observed_count",
                        "avg_minutes", "escalation_rate"]].rename(columns={
            "observed_count": "count", "volume_basis": "count is"})
        st.dataframe(show, width="stretch", hide_index=True)
        with st.expander("Source files"):
            st.dataframe(pd.DataFrame(b.sources), width="stretch", hide_index=True)
        st.info("Next: open **② AI analysis**.")
    else:
        st.caption("Load data to begin.")

# ----------------------------------------------------------------------------- 2. analysis
with t_ai:
    st.subheader("AI analysis")
    b = st.session_state.bundle
    if b is None:
        st.caption("Load data in ① first.")
    else:
        live = mode.startswith("Live")
        label = "Run analysis with Claude" if live else "Show saved analysis of the sample data"
        if st.button(label, type="primary"):
            try:
                if live:
                    if not (api_key or has_env_key):
                        st.error("Add an Anthropic API key in the sidebar.")
                        st.stop()
                    runs = st.session_state.get("live_runs", 0)
                    if not api_key and runs >= 3:
                        st.error("Live-run limit reached for this session on the hosted key. "
                                 "Add your own API key in the sidebar to continue.")
                        st.stop()
                    st.session_state.live_runs = runs + 1
                    with st.spinner("Claude is reading the task profile and evidence…"):
                        result = analyze(b, COMPANY_CONTEXT if st.session_state.get("is_sample") else "",
                                         model=model, api_key=api_key)
                else:
                    if not st.session_state.get("is_sample", True):
                        st.error("Demo mode only has a saved analysis for the sample data.")
                        st.stop()
                    result = load_cached(str(DEMO_CACHE))
                st.session_state.analysis = result
                st.session_state.validation = validate(result, b)
                st.session_state.review = seed_review(result)
            except Exception as e:
                st.error(f"Analysis failed: {e}")

        an, v = st.session_state.analysis, st.session_state.validation
        if an:
            meta = an.get("_meta", {})
            if meta.get("source") == "illustrative":
                st.caption("Showing an illustrative saved analysis of the sample data. Switch to Live "
                           "mode with an API key to generate a fresh one.")
            else:
                st.caption(f"Model: {meta.get('model')} · tokens in/out: "
                           f"{meta.get('input_tokens')}/{meta.get('output_tokens')} · source: {meta.get('source')}")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Opportunities", len(an["opportunities"]))
            m2.metric("Citations verified", f"{v['citation_valid']}/{v['citation_total']}")
            m3.metric("Grounding rate", f"{v['grounding_rate']:.0%}")
            m4.metric("Opportunities with issues", v["opportunities_with_issues"])

            st.markdown(f"**Summary.** {an['summary']}")
            st.divider()
            for o in an["opportunities"]:
                issues = v["per_opportunity"].get(o["id"], [])
                flag = " ⚠️" if issues else " ✅"
                with st.expander(f"{o['id']} · {o['title']}{flag}"):
                    st.markdown(
                        f'<span class="pill">{o["process"]}</span><span class="pill">{o["automation_pattern"]}</span>'
                        f'<span class="pill">feasibility {o["feasibility"]}/5</span>'
                        f'<span class="pill">risk {o["risk"]}/5</span><span class="pill">complexity {o["complexity"]}</span>',
                        unsafe_allow_html=True)
                    st.markdown(f"**Problem.** {o['problem']}")
                    st.markdown(f"**Proposed solution.** {o['proposed_solution']}")
                    st.markdown(f"**What stays human.** {o['human_role']}")
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Why feasible.** {o['feasibility_rationale']}")
                    c2.markdown(f"**Risk.** {o['risk_rationale']}")
                    st.markdown(f"**Suggested assumptions** (editable in ③): automate "
                                f"{o['suggested_automatable_share']:.0%} of task time, keep "
                                f"{o['suggested_review_overhead']:.0%} of saved time for human review.")
                    st.markdown("**Evidence** — click to see the exact source")
                    for e in o["evidence"]:
                        sid = e["source_id"]
                        src = b.records.get(sid) or b.paragraphs.get(sid)
                        ok = "✅" if src is not None else "❌ not found"
                        with st.popover(f"{sid} {ok} — {e['why']}"):
                            if isinstance(src, dict):
                                st.json(src)
                            elif src:
                                st.write(src)
                            else:
                                st.error("This citation does not exist in the uploaded sources.")
                    if o.get("open_questions"):
                        st.markdown("**Open questions**")
                        for q in o["open_questions"]:
                            st.markdown(f"- {q}")
                    for i in issues:
                        st.warning(i)
            if an.get("not_recommended"):
                st.markdown("#### Deliberately not recommended")
                st.dataframe(pd.DataFrame(an["not_recommended"]), width="stretch", hide_index=True)
            st.info("Next: open **③ Review & approve**.")

# ----------------------------------------------------------------------------- 3. review
with t_rev:
    st.subheader("Human review")
    if st.session_state.review is None:
        st.caption("Run the analysis in ② first.")
    else:
        st.markdown("Approve, reject or edit each recommendation. Assumptions start at Claude's suggestions; "
                    "anything you change here flows straight into the savings model.")
        q1, q2, _ = st.columns([1, 1, 3])
        if q1.button("Approve all risk ≤ 3"):
            df = st.session_state.review
            df.loc[df["risk"] <= 3, "decision"] = "Approved"
        if q2.button("Reset to suggestions"):
            st.session_state.review = seed_review(st.session_state.analysis)

        edited = st.data_editor(
            st.session_state.review, width="stretch", hide_index=True, key="review_editor",
            disabled=["id", "title"],
            column_config={
                "decision": st.column_config.SelectboxColumn("Decision", options=DECISIONS, required=True),
                "automatable_share": st.column_config.NumberColumn("Automatable share", min_value=0.0,
                                                                   max_value=1.0, step=0.05, format="%.2f"),
                "review_overhead": st.column_config.NumberColumn("Review overhead", min_value=0.0,
                                                                 max_value=1.0, step=0.05, format="%.2f"),
                "complexity": st.column_config.SelectboxColumn("Complexity", options=["S", "M", "L"]),
                "feasibility": st.column_config.NumberColumn("Feasibility", min_value=1, max_value=5, step=1),
                "risk": st.column_config.NumberColumn("Risk", min_value=1, max_value=5, step=1),
                "reviewer_note": st.column_config.TextColumn("Reviewer note", width="large"),
            })
        st.session_state.review = edited

        base = seed_review(st.session_state.analysis).set_index("id")
        cur = edited.set_index("id")
        cols = ["automatable_share", "review_overhead", "complexity", "feasibility", "risk"]
        changed = [(i, c) for i in cur.index for c in cols if cur.at[i, c] != base.at[i, c]]
        counts = edited["decision"].value_counts()
        st.caption(f"Approved {counts.get('Approved', 0)} · Pending {counts.get('Pending', 0)} · "
                   f"Needs info {counts.get('Needs more info', 0)} · Rejected {counts.get('Rejected', 0)} · "
                   f"{len(changed)} assumption(s) changed from the AI suggestion")
        if changed:
            st.caption("Changed: " + ", ".join(f"{i}.{c}" for i, c in changed))

# ----------------------------------------------------------------------------- 4. ROI
with t_roi:
    st.subheader("ROI estimates and roadmap")
    an, rv = st.session_state.analysis, st.session_state.review
    if an is None or rv is None:
        st.caption("Complete ② and ③ first.")
    else:
        overrides = {r["id"]: {k: r[k] for k in ["automatable_share", "review_overhead", "complexity",
                                                 "feasibility", "risk"]}
                     for r in rv.to_dict(orient="records")}
        roi = compute(an["opportunities"], st.session_state.bundle.tasks, a, overrides)
        decisions = dict(zip(rv["id"], rv["decision"]))
        notes = {k: v for k, v in zip(rv["id"], rv["reviewer_note"]) if v}
        roi["decision"] = roi["id"].map(decisions)

        scope = st.radio("Show", ["Approved only", "All opportunities"], horizontal=True)
        view = roi[roi["decision"] == "Approved"] if scope == "Approved only" else roi
        if view.empty:
            st.warning("Nothing approved yet. Approve opportunities in ③, or switch to 'All opportunities'.")
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Est. net hours saved / month", f"{view['net_hours_saved_m'].sum():,.0f}",
                      help="After subtracting human review time")
            k2.metric("≈ FTE capacity freed", f"{view['fte_equivalent'].sum():.1f}", help="160 hours = 1 FTE")
            k3.metric("Est. annual net value", f"${view['annual_net_value_usd'].sum():,.0f}",
                      help="Labor value minus run cost; excludes build cost")
            k4.metric("Est. one-time build cost", f"${view['build_cost_usd'].sum():,.0f}")

            c1, c2 = st.columns([3, 2])
            fig = px.scatter(view, x="risk", y="annual_net_value_usd", size="net_hours_saved_m",
                             color="phase", text="id", size_max=45,
                             hover_data=["title", "feasibility", "payback_months"],
                             labels={"risk": "Risk (1 low – 5 high)", "annual_net_value_usd": "Annual net value (USD)"},
                             color_discrete_sequence=["#1F6F4A", "#1F3A5F", "#B5651D"])
            fig.update_traces(textposition="top center")
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), legend_title_text="",
                              legend=dict(orientation="h", y=-0.2), xaxis=dict(range=[0.5, 5.5], dtick=1))
            c1.markdown("**Value vs. risk** (bubble = hours saved)")
            c1.plotly_chart(fig, width="stretch")

            bar = px.bar(view.sort_values("priority_score"), x="priority_score", y="id", orientation="h",
                         color="phase", hover_data=["title"],
                         labels={"priority_score": "Priority score (0–100)", "id": ""},
                         color_discrete_sequence=["#1F6F4A", "#1F3A5F", "#B5651D"])
            bar.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
            c2.markdown("**Priority ranking**")
            c2.plotly_chart(bar, width="stretch")

            st.markdown("**Roadmap**")
            for phase, g in view.groupby("phase", sort=True):
                st.markdown(f"**Phase {phase}**")
                for r in g.itertuples():
                    st.markdown(f"- **{r.id} · {r.title}** — {r.net_hours_saved_m:,.0f} h/mo · "
                                f"${r.annual_net_value_usd:,.0f}/yr · payback {r.payback_months} mo")

            with st.expander("Full calculation table"):
                st.dataframe(view, width="stretch", hide_index=True)
                st.caption("net_hours = volume × avg_minutes ÷ 60 × automatable_share × (1 − review_overhead). "
                           "Phase 3 if risk ≥ gate, complexity L or negative net value; Phase 1 if "
                           "feasibility ≥ 4, risk ≤ 2 and complexity S.")

        st.divider()
        md = build_markdown(roi, an, decisions, notes, {
            "Loaded cost per hour (USD)": a.loaded_hourly_cost,
            "Support sample multiplier": a.sample_multipliers["SUP"],
            "Compliance sample multiplier": a.sample_multipliers["CMP"],
            "Build cost per week (USD)": a.weekly_build_cost,
            "Build weeks S/M/L": "/".join(str(a.build_weeks[k]) for k in "SML"),
            "Monthly run cost S/M/L (USD)": "/".join(str(int(a.monthly_run_cost[k])) for k in "SML"),
            "Weights value/feasibility/risk": f"{a.weight_value}/{a.weight_feasibility}/{a.weight_risk}",
            "Risk gate": a.risk_gate,
        })
        audit = {"generated_at": datetime.now().isoformat(timespec="seconds"), "analysis": an,
                 "validation": st.session_state.validation, "review": rv.to_dict(orient="records"),
                 "assumptions": a.to_dict()}
        d1, d2, d3 = st.columns(3)
        d1.download_button("⬇ Implementation roadmap (.md)", md, "ai_automation_roadmap.md", "text/markdown",
                           type="primary", width="stretch")
        d2.download_button("⬇ ROI table (.csv)", roi.to_csv(index=False), "roi_estimates.csv", "text/csv",
                           width="stretch")
        d3.download_button("⬇ Audit trail (.json)", json.dumps(audit, indent=2, default=str),
                           "audit_trail.json", "application/json", width="stretch")

# ----------------------------------------------------------------------------- how it works
with t_how:
    st.subheader("How it works")
    st.markdown("""
| Step | Who does it | Why |
|---|---|---|
| Profile volumes and handle times | **Code** (`mapper/ingest.py`) | Numbers come from data, never from the model |
| Find opportunities, explain, score feasibility & risk, cite evidence | **Claude** (`mapper/llm.py`) | Judgment and synthesis across messy notes and records |
| Check citations exist, task links are real, regulated steps keep a human | **Code** (`mapper/validate.py`) | Catch hallucinated sources before a person sees them |
| Calculate hours, value, payback and phase | **Code** (`mapper/roi.py`) | Transparent, reproducible, editable assumptions |
| Approve, reject, edit assumptions | **Human** (tab ③) | Accountability stays with the business |

**What this demo does not prove.** All data is synthetic and every savings figure is an estimate. Real impact
requires a pilot: measure handle time and error rates on the same task mix for four weeks before and after launch.
""")
    st.caption("Built by Bee as an AI strategy portfolio project. Kestrel Pay is fictional.")
