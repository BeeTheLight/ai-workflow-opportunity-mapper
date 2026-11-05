"""Guardrails on the model's output before a human ever sees it.

Checks every opportunity for: task_keys that exist in the profile, evidence IDs that exist
in the uploaded sources, scores in range, and regulated work not being handed to AI to
decide. Failures are surfaced in the UI, not silently fixed.
"""
from __future__ import annotations

import re

from .ingest import SourceBundle

REGULATED_TERMS = re.compile(
    r"\b(sanction|pep|sar|str|suspicious|mlro|approv|declin|high-risk|edd|due diligence)\w*", re.I)
AUTONOMY_TERMS = re.compile(r"\b(auto[- ]?(close|clear|approve|decline|reject|file)|without (human|analyst) review)\b", re.I)


def validate(analysis: dict, bundle: SourceBundle) -> dict:
    valid_tasks = set(bundle.tasks["task_key"])
    valid_ids = bundle.valid_ids
    per_opp, total_cites, good_cites = {}, 0, 0

    for opp in analysis.get("opportunities", []):
        issues = []
        bad_tasks = [k for k in opp.get("task_keys", []) if k not in valid_tasks]
        if bad_tasks:
            issues.append(f"Unknown task_keys (ignored in ROI): {', '.join(bad_tasks)}")
        if not [k for k in opp.get("task_keys", []) if k in valid_tasks]:
            issues.append("No valid task linked; savings cannot be calculated.")

        ev = opp.get("evidence", [])
        cited = [e.get("source_id", "") for e in ev]
        bad_cites = [c for c in cited if c not in valid_ids]
        total_cites += len(cited)
        good_cites += len(cited) - len(bad_cites)
        if bad_cites:
            issues.append(f"Citations not found in sources: {', '.join(bad_cites)}")
        if len(cited) - len(bad_cites) < 2:
            issues.append("Fewer than two verifiable citations.")
        if not any(c in bundle.paragraphs for c in cited):
            issues.append("No qualitative evidence (interview/SOP) cited.")

        for f in ("feasibility", "risk"):
            if not isinstance(opp.get(f), int) or not 1 <= opp[f] <= 5:
                issues.append(f"{f} out of range: {opp.get(f)}")
        for f in ("suggested_automatable_share", "suggested_review_overhead"):
            v = opp.get(f)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                issues.append(f"{f} out of range: {v}")

        text = " ".join(str(opp.get(k, "")) for k in ("title", "problem", "proposed_solution"))
        if REGULATED_TERMS.search(text) and AUTONOMY_TERMS.search(text):
            issues.append("Proposes autonomous decisions in a regulated step. Requires human sign-off.")
        if REGULATED_TERMS.search(text) and opp.get("risk", 5) < 3:
            issues.append("Regulated step scored as low risk; check the risk score.")

        per_opp[opp.get("id", "?")] = issues

    return {
        "per_opportunity": per_opp,
        "citation_total": total_cites,
        "citation_valid": good_cites,
        "grounding_rate": round(good_cites / total_cites, 3) if total_cites else 0.0,
        "opportunities_with_issues": sum(1 for v in per_opp.values() if v),
    }
