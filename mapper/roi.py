"""Deterministic savings and prioritization. No LLM calls in this file.

For each opportunity:
  monthly_volume   = Σ over linked tasks: observed_count × sample multiplier   (or monthly volume as-is)
  baseline_hours   = Σ volume × avg_minutes / 60
  gross_hours      = baseline_hours × automatable_share
  net_hours        = gross_hours × (1 − review_overhead)           ← time a human still spends checking
  monthly_value    = net_hours × loaded_hourly_cost
  build_cost       = build_weeks[complexity] × weekly_build_cost
  payback_months   = build_cost / (monthly_value − monthly_run_cost)

Priority score (0–100) = weighted blend of normalized value, feasibility and (inverse) risk.
Every input is either computed from data or an explicit, editable assumption.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass
class Assumptions:
    loaded_hourly_cost: float = 28.0          # USD, blended fully-loaded ops cost
    sample_multipliers: dict = field(default_factory=lambda: {
        "SUP": 20.0,   # 200 sampled tickets of ~4,000/month
        "CMP": 10.0,   # 150 sampled reviews of ~1,500/month
    })
    default_sample_multiplier: float = 1.0
    weekly_build_cost: float = 4500.0         # USD per build-week (eng + PM time)
    build_weeks: dict = field(default_factory=lambda: {"S": 2, "M": 6, "L": 12})
    monthly_run_cost: dict = field(default_factory=lambda: {"S": 150.0, "M": 600.0, "L": 1500.0})
    weight_value: float = 0.5
    weight_feasibility: float = 0.3
    weight_risk: float = 0.2
    risk_gate: int = 4                        # risk >= gate → Phase 3 regardless of score

    def to_dict(self) -> dict:
        return asdict(self)


def _multiplier(task_key: str, basis: str, a: Assumptions) -> float:
    if basis == "monthly":
        return 1.0
    return float(a.sample_multipliers.get(task_key.split(":")[0], a.default_sample_multiplier))


def compute(opportunities: list[dict], tasks: pd.DataFrame, a: Assumptions,
            overrides: dict[str, dict] | None = None) -> pd.DataFrame:
    """overrides: {opp_id: {"automatable_share": x, "review_overhead": y, "complexity": "M", ...}}"""
    overrides = overrides or {}
    t = tasks.set_index("task_key")
    rows = []
    for opp in opportunities:
        o = overrides.get(opp["id"], {})
        keys = [k for k in opp.get("task_keys", []) if k in t.index]
        vol = hours = 0.0
        for k in keys:
            r = t.loc[k]
            v = float(r["observed_count"]) * _multiplier(k, r["volume_basis"], a)
            vol += v
            hours += v * float(r["avg_minutes"] or 0) / 60.0

        share = float(o.get("automatable_share", opp.get("suggested_automatable_share", 0)))
        overhead = float(o.get("review_overhead", opp.get("suggested_review_overhead", 0)))
        complexity = o.get("complexity", opp.get("complexity", "M"))
        feas = int(o.get("feasibility", opp.get("feasibility", 3)))
        risk = int(o.get("risk", opp.get("risk", 3)))

        gross = hours * share
        net = gross * (1 - overhead)
        value_m = net * a.loaded_hourly_cost
        build = a.build_weeks.get(complexity, 6) * a.weekly_build_cost
        run_m = a.monthly_run_cost.get(complexity, 600.0)
        net_value_m = value_m - run_m
        payback = build / net_value_m if net_value_m > 0 else float("inf")

        rows.append({
            "id": opp["id"], "title": opp["title"], "process": opp.get("process", ""),
            "pattern": opp.get("automation_pattern", ""), "tasks_linked": len(keys),
            "monthly_volume": round(vol), "baseline_hours_m": round(hours, 1),
            "automatable_share": share, "review_overhead": overhead,
            "net_hours_saved_m": round(net, 1), "fte_equivalent": round(net / 160, 2),
            "monthly_value_usd": round(value_m), "monthly_run_cost_usd": round(run_m),
            "annual_net_value_usd": round(net_value_m * 12),
            "build_cost_usd": round(build), "payback_months": round(payback, 1),
            "feasibility": feas, "risk": risk, "complexity": complexity,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    vmax = df["annual_net_value_usd"].clip(lower=0).max() or 1
    wsum = a.weight_value + a.weight_feasibility + a.weight_risk or 1
    df["priority_score"] = (100 * (
        a.weight_value * df["annual_net_value_usd"].clip(lower=0) / vmax
        + a.weight_feasibility * (df["feasibility"] - 1) / 4
        + a.weight_risk * (5 - df["risk"]) / 4
    ) / wsum).round(1)
    df["phase"] = df.apply(lambda r: assign_phase(r, a), axis=1)
    return df.sort_values(["phase", "priority_score"], ascending=[True, False]).reset_index(drop=True)


def assign_phase(r, a: Assumptions) -> str:
    if r["risk"] >= a.risk_gate or r["complexity"] == "L" or r["annual_net_value_usd"] <= 0:
        return "3 · Later / needs controls (90+ days)"
    if r["feasibility"] >= 4 and r["risk"] <= 2 and r["complexity"] == "S":
        return "1 · Quick wins (0–30 days)"
    return "2 · Next (30–90 days)"
