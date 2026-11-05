"""The AI step: Claude reads the deterministic task profile plus the source evidence and
returns structured opportunities with reasoning and citations.

What the model is allowed to decide:   which tasks are good candidates, why, how,
                                        feasibility/risk scores, and *suggested* assumptions.
What the model is NOT allowed to decide: volumes, handle times, costs, savings. Those
                                        come from ingest.py + roi.py.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .ingest import SourceBundle

DEFAULT_MODEL = os.getenv("MAPPER_MODEL", "claude-sonnet-5-5")

PATTERNS = [
    "Deterministic rules / RPA",
    "Retrieval-grounded self-service",
    "LLM classification and routing",
    "Document extraction and verification",
    "LLM drafting with human review",
    "Agentic case preparation",
]

SYSTEM_PROMPT = """You are an enterprise operations analyst who specializes in finding \
practical AI and automation opportunities in regulated financial services.

You will receive (1) a task profile computed from the company's own operational data and \
(2) evidence: sample records and paragraphs from interview notes and SOPs, each with an ID.

Your job:
- Identify the best automation opportunities. Each opportunity must map to one or more \
task_keys from the profile. Do not invent tasks.
- Explain your reasoning in plain business language.
- Cite evidence by ID for every opportunity (at least two IDs, ideally one record and one \
document paragraph). Only cite IDs that appear in the input.
- Score feasibility (1 = hard, 5 = easy with today's tools) and risk (1 = low, 5 = high: \
regulatory, customer harm, or reputational exposure if the automation is wrong).
- Suggest, but do not calculate, two assumptions: the share of task time that could be \
automated, and the share of saved time that must be spent on human review. Be conservative.
- State explicitly what remains a human decision. In regulated steps (sanctions, SAR/STR, \
merchant approval) AI may prepare and summarize, never decide.
- List tasks you deliberately did NOT recommend and why. Good judgment about what not to \
automate matters as much as what to automate.

Never compute hours, costs or savings. Downstream code does that from the data."""

OPPORTUNITY_TOOL = {
    "name": "submit_opportunity_map",
    "description": "Submit the ranked list of automation opportunities with reasoning and citations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "3-4 sentence executive summary of the findings."},
            "opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "OPP-01, OPP-02, ..."},
                        "title": {"type": "string"},
                        "process": {"type": "string"},
                        "task_keys": {"type": "array", "items": {"type": "string"}},
                        "problem": {"type": "string", "description": "What is manual and why it hurts."},
                        "proposed_solution": {"type": "string"},
                        "automation_pattern": {"type": "string", "enum": PATTERNS},
                        "human_role": {"type": "string", "description": "What stays with a person."},
                        "feasibility": {"type": "integer", "minimum": 1, "maximum": 5},
                        "feasibility_rationale": {"type": "string"},
                        "risk": {"type": "integer", "minimum": 1, "maximum": 5},
                        "risk_rationale": {"type": "string"},
                        "complexity": {"type": "string", "enum": ["S", "M", "L"]},
                        "suggested_automatable_share": {"type": "number", "minimum": 0, "maximum": 1},
                        "suggested_review_overhead": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"source_id": {"type": "string"}, "why": {"type": "string"}},
                                "required": ["source_id", "why"],
                            },
                        },
                        "open_questions": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "id", "title", "process", "task_keys", "problem", "proposed_solution",
                        "automation_pattern", "human_role", "feasibility", "feasibility_rationale",
                        "risk", "risk_rationale", "complexity", "suggested_automatable_share",
                        "suggested_review_overhead", "evidence",
                    ],
                },
            },
            "not_recommended": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"task_key": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["task_key", "reason"],
                },
            },
        },
        "required": ["summary", "opportunities", "not_recommended"],
    },
}


def build_context(bundle: SourceBundle, company_context: str = "") -> str:
    """Render the profile + evidence as a compact, ID-tagged brief for the model."""
    lines = []
    if company_context:
        lines += ["## Company context", company_context.strip(), ""]
    lines.append("## Task profile (computed from data)")
    for t in bundle.tasks.to_dict(orient="records"):
        basis = "per month" if t["volume_basis"] == "monthly" else "in sample window"
        esc = f", escalation {t['escalation_rate']:.0%}" if t.get("escalation_rate") is not None else ""
        extra = "; ".join(f"{k}={v}" for k, v in (t.get("extra") or {}).items())
        lines.append(
            f"- task_key={t['task_key']} | process={t['process']} | task={t['task']} | "
            f"{int(t['observed_count'])} {basis} | avg {t['avg_minutes']} min{esc}"
            + (f" | {extra}" if extra else "")
        )
        for eid in t["example_ids"][:3]:
            rec = bundle.records.get(eid, {})
            snippet = rec.get("description") or rec.get("notes") or ""
            lines.append(f"    · [{eid}] {str(snippet)[:200]}")
    lines += ["", "## Document evidence"]
    for pid, text in bundle.paragraphs.items():
        lines.append(f"[{pid}] {text}")
    return "\n".join(lines)


def analyze(bundle: SourceBundle, company_context: str = "", model: str | None = None,
            api_key: str | None = None) -> dict[str, Any]:
    """Call Claude with a forced tool call so the output is always schema-shaped JSON."""
    import anthropic  # imported lazily so demo mode works without the SDK configured

    client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=8000,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        tools=[OPPORTUNITY_TOOL],
        tool_choice={"type": "tool", "name": OPPORTUNITY_TOOL["name"]},
        messages=[{
            "role": "user",
            "content": build_context(bundle, company_context)
            + "\n\nIdentify 5-8 opportunities, ranked by your judgment of overall value. "
              "Then submit with the tool.",
        }],
    )
    block = next(b for b in resp.content if b.type == "tool_use")
    result = dict(block.input)
    result["_meta"] = {
        "model": resp.model,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "source": "live",
    }
    return result


def load_cached(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
