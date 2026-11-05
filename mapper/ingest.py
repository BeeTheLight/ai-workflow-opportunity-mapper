"""Turn raw uploads (CSVs + markdown/text notes) into a deterministic task profile.

Design rule: every number the ROI model uses (volumes, handle times) is computed here,
from the data, by plain code. The LLM never supplies volumes or minutes.

Each source unit gets a stable ID so the LLM can cite it and we can verify the citation:
  - CSV rows keep their own ID column (SUP-0001, ONB-03, CMP-0042) or get ROW-<file>-<n>
  - Markdown/text documents are split into paragraphs: <PREFIX>-P01, <PREFIX>-P02, ...
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pandas as pd

# --------------------------------------------------------------------------- schemas
# Known schemas are recognized by their columns. Anything else falls back to GENERIC,
# which needs a "what is the task" column and a "how many minutes" column.
SCHEMAS = {
    "support_cases": {
        "required": {"case_id", "category", "handle_time_min"},
        "process": "Customer support",
        "id_col": "case_id", "task_col": "category", "minutes_col": "handle_time_min",
        "volume": "sample", "escalation_col": "escalated", "text_col": "description",
    },
    "compliance_reviews": {
        "required": {"review_id", "review_type", "minutes_spent"},
        "process": "Compliance operations",
        "id_col": "review_id", "task_col": "review_type", "minutes_col": "minutes_spent",
        "volume": "sample", "escalation_col": None, "text_col": "notes",
    },
    "process_map": {
        "required": {"step_id", "step_name", "monthly_volume", "avg_minutes"},
        "process": "Merchant onboarding",
        "id_col": "step_id", "task_col": "step_name", "minutes_col": "avg_minutes",
        "volume": "monthly", "escalation_col": None, "text_col": "notes",
    },
}
TASK_COL_GUESSES = ["task", "task_name", "category", "activity", "step", "step_name", "type"]
MIN_COL_GUESSES = ["minutes", "handle_time_min", "avg_minutes", "duration_min", "time_min", "minutes_spent"]


@dataclass
class SourceBundle:
    tasks: pd.DataFrame                       # one row per task candidate (deterministic profile)
    records: dict[str, dict]                  # source_id -> row dict (all CSV rows)
    paragraphs: dict[str, str]                # source_id -> paragraph text (docs)
    sources: list[dict] = field(default_factory=list)   # file-level metadata
    warnings: list[str] = field(default_factory=list)

    @property
    def valid_ids(self) -> set[str]:
        return set(self.records) | set(self.paragraphs)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:60]


def _detect_schema(df: pd.DataFrame) -> tuple[str, dict]:
    cols = set(df.columns)
    for name, spec in SCHEMAS.items():
        if spec["required"] <= cols:
            return name, spec
    task_col = next((c for c in TASK_COL_GUESSES if c in cols), None)
    min_col = next((c for c in MIN_COL_GUESSES if c in cols), None)
    if task_col and min_col:
        return "generic", {
            "process": "Uploaded process", "id_col": None, "task_col": task_col,
            "minutes_col": min_col, "volume": "monthly" if "monthly_volume" in cols else "sample",
            "escalation_col": "escalated" if "escalated" in cols else None,
            "text_col": next((c for c in ["description", "notes", "details"] if c in cols), None),
        }
    raise ValueError(
        "Could not recognize this CSV. Include a task/category column and a minutes column "
        f"(looked for {TASK_COL_GUESSES} and {MIN_COL_GUESSES})."
    )


def _profile_csv(name: str, df: pd.DataFrame, bundle: SourceBundle) -> None:
    schema, spec = _detect_schema(df)
    df = df.copy()
    prefix = {"support_cases": "SUP", "compliance_reviews": "CMP", "process_map": "ONB"}.get(
        schema, _slug(name.rsplit(".", 1)[0]).upper()[:10])
    if spec["id_col"] is None:
        df["_id"] = [f"ROW-{prefix}-{i:04d}" for i in range(1, len(df) + 1)]
        id_col = "_id"
    else:
        id_col = spec["id_col"]

    minutes = pd.to_numeric(df[spec["minutes_col"]], errors="coerce")
    missing = int(minutes.isna().sum())
    if missing:
        bundle.warnings.append(
            f"{name}: {missing} row(s) missing {spec['minutes_col']}; excluded from the time average, kept in volume."
        )
    df["_minutes"] = minutes

    for row in df.to_dict(orient="records"):
        bundle.records[str(row[id_col])] = {k: v for k, v in row.items() if not str(k).startswith("_")}

    rows = []
    for task, g in df.groupby(spec["task_col"], sort=False):
        esc = None
        if spec["escalation_col"] and spec["escalation_col"] in g:
            esc = round(float((g[spec["escalation_col"]].astype(str).str.lower() == "yes").mean()), 3)
        if spec["volume"] == "monthly":
            vol = float(pd.to_numeric(g["monthly_volume"], errors="coerce").sum())
        else:
            vol = float(len(g))
        rows.append({
            "task_key": f"{prefix}:{_slug(task)}",
            "process": spec["process"],
            "task": str(task),
            "source_file": name,
            "volume_basis": spec["volume"],          # "sample" -> scaled by an assumption; "monthly" -> as-is
            "observed_count": vol,
            "avg_minutes": round(float(g["_minutes"].mean()), 1) if g["_minutes"].notna().any() else None,
            "escalation_rate": esc,
            "example_ids": [str(x) for x in g[id_col].head(4)],
            "example_text": [str(x)[:220] for x in g[spec["text_col"]].head(3)] if spec["text_col"] else [],
            "extra": {k: g[k].iloc[0] for k in ("owner_role", "rework_rate", "regulatory_sensitivity", "systems")
                      if k in g and len(g) == 1},
        })
    bundle.sources.append({"file": name, "kind": schema, "rows": len(df), "tasks": len(rows), "prefix": prefix})
    bundle.tasks = pd.concat([bundle.tasks, pd.DataFrame(rows)], ignore_index=True)


def _profile_doc(name: str, text: str, bundle: SourceBundle) -> None:
    stem = name.rsplit(".", 1)[0].lower()
    prefix = "NOTES" if "interview" in stem or "notes" in stem else ("SOP" if "sop" in stem else _slug(stem).upper()[:8])
    heading, n = "", 0
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            heading = block.lstrip("# ").splitlines()[0]
            rest = "\n".join(block.splitlines()[1:]).strip()
            if not rest:
                continue
            block = rest
        n += 1
        pid = f"{prefix}-P{n:02d}"
        bundle.paragraphs[pid] = f"[{heading}] {block}" if heading else block
    bundle.sources.append({"file": name, "kind": "document", "paragraphs": n, "prefix": prefix})


def load_sources(files: list[tuple[str, bytes]]) -> SourceBundle:
    """files: list of (filename, raw bytes). CSV -> profiled; .md/.txt -> paragraphs."""
    bundle = SourceBundle(tasks=pd.DataFrame(), records={}, paragraphs={})
    for name, raw in files:
        lower = name.lower()
        if lower.endswith(".csv"):
            _profile_csv(name, pd.read_csv(io.BytesIO(raw)), bundle)
        elif lower.endswith((".md", ".txt")):
            _profile_doc(name, raw.decode("utf-8", errors="replace"), bundle)
        else:
            bundle.warnings.append(f"{name}: unsupported type (use .csv, .md or .txt); skipped.")
    if bundle.tasks.empty:
        raise ValueError("No process data found. Upload at least one CSV of tasks, cases or process steps.")
    return bundle
