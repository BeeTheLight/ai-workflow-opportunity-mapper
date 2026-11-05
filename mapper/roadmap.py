"""Export the approved plan as a markdown roadmap a stakeholder can read without the app."""
from __future__ import annotations

from datetime import date

import pandas as pd

DISCLAIMER = (
    "All savings are **estimates** computed from the uploaded data and the assumptions listed "
    "below. They are not observed results. Impact should be measured in a pilot against a "
    "baseline before any figure is reported as achieved."
)


def _money(x: float) -> str:
    return f"${x:,.0f}"


def build_markdown(roi: pd.DataFrame, analysis: dict, approvals: dict, notes: dict,
                   assumptions: dict, company: str = "Kestrel Pay (fictional)") -> str:
    opps = {o["id"]: o for o in analysis.get("opportunities", [])}
    approved = roi[roi["id"].map(lambda i: approvals.get(i) == "Approved")]
    held = roi[roi["id"].map(lambda i: approvals.get(i) != "Approved")]

    out = [
        f"# AI automation roadmap — {company}",
        f"_Generated {date.today():%B %d, %Y} by AI Workflow Opportunity Mapper. "
        f"Analysis source: {analysis.get('_meta', {}).get('source', 'unknown')}, "
        f"model: {analysis.get('_meta', {}).get('model', 'n/a')}._",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Summary",
        analysis.get("summary", ""),
        "",
        f"**Approved opportunities:** {len(approved)} of {len(roi)}  ",
        f"**Estimated net hours saved / month:** {approved['net_hours_saved_m'].sum():,.0f} "
        f"(≈ {approved['fte_equivalent'].sum():.1f} FTE)  ",
        f"**Estimated annual net value:** {_money(approved['annual_net_value_usd'].sum())}  ",
        f"**Estimated one-time build cost:** {_money(approved['build_cost_usd'].sum())}",
        "",
    ]

    for phase, g in approved.groupby("phase", sort=True):
        out += [f"## Phase {phase}", ""]
        for r in g.itertuples():
            o = opps.get(r.id, {})
            out += [
                f"### {r.id} · {r.title}",
                f"*{r.process} · {r.pattern} · feasibility {r.feasibility}/5 · risk {r.risk}/5 · complexity {r.complexity}*",
                "",
                f"**Problem.** {o.get('problem', '')}",
                "",
                f"**Proposed solution.** {o.get('proposed_solution', '')}",
                "",
                f"**What stays human.** {o.get('human_role', '')}",
                "",
                f"**Estimate.** {r.monthly_volume:,} items/month · {r.net_hours_saved_m:,.0f} net hours/month "
                f"· {_money(r.annual_net_value_usd)}/yr net · build {_money(r.build_cost_usd)} "
                f"· payback {r.payback_months} months",
                "",
                "**Evidence.** " + "; ".join(
                    f"`{e['source_id']}` {e['why']}" for e in o.get("evidence", [])),
                "",
            ]
            if notes.get(r.id):
                out += [f"**Reviewer note.** {notes[r.id]}", ""]
            if o.get("open_questions"):
                out += ["**Open questions.**"] + [f"- {q}" for q in o["open_questions"]] + [""]
            out += ["**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks "
                    "before and after launch on the same task mix.", ""]

    if len(held):
        out += ["## Not approved / on hold", ""]
        for r in held.itertuples():
            out.append(f"- **{r.id} · {r.title}** — {approvals.get(r.id, 'Pending')}"
                       + (f": {notes[r.id]}" if notes.get(r.id) else ""))
        out.append("")

    if analysis.get("not_recommended"):
        out += ["## Deliberately not recommended for automation", ""]
        out += [f"- `{n['task_key']}` — {n['reason']}" for n in analysis["not_recommended"]]
        out.append("")

    out += ["## Assumptions used", "", "| Assumption | Value |", "|---|---|"]
    for k, v in assumptions.items():
        out.append(f"| {k} | {v} |")
    out += ["", "## Method", "",
            "1. Task volumes and handle times computed directly from uploaded data.",
            "2. Claude identified opportunities, scored feasibility and risk, and cited source records.",
            "3. Citations and task links were machine-checked against the sources.",
            "4. Savings were calculated by deterministic code from the assumptions above.",
            "5. A human reviewer approved, edited or rejected each opportunity."]
    return "\n".join(out)
