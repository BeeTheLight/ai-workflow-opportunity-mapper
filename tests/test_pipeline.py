"""Unit tests for the deterministic parts: ingest, validation and ROI math."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapper.ingest import load_sources  # noqa: E402
from mapper.roi import Assumptions, compute  # noqa: E402
from mapper.validate import validate  # noqa: E402


@pytest.fixture(scope="module")
def bundle():
    return load_sources([(p.name, p.read_bytes()) for p in sorted((ROOT / "data").iterdir())])


@pytest.fixture(scope="module")
def analysis():
    return json.loads((ROOT / "sample_output" / "demo_analysis.json").read_text())


def test_ingest_profiles_all_sources(bundle):
    assert len(bundle.records) == 200 + 10 + 150
    assert {"SUP", "ONB", "CMP"} == {k.split(":")[0] for k in bundle.tasks["task_key"]}
    assert any("missing handle_time_min" in w for w in bundle.warnings)
    assert "NOTES-P02" in bundle.paragraphs and "SOP-P02" in bundle.paragraphs


def test_generic_csv_is_accepted():
    csv = b"task,minutes\nInvoice matching,12\nInvoice matching,14\nVendor setup,30\n"
    b = load_sources([("finance_ops.csv", csv)])
    assert len(b.tasks) == 2
    assert b.tasks.loc[b.tasks.task == "Invoice matching", "avg_minutes"].item() == 13.0


def test_unrecognized_csv_raises():
    with pytest.raises(ValueError):
        load_sources([("bad.csv", b"a,b\n1,2\n")])


def test_demo_analysis_is_fully_grounded(bundle, analysis):
    v = validate(analysis, bundle)
    assert v["grounding_rate"] == 1.0
    assert v["opportunities_with_issues"] == 0


def test_validator_catches_hallucinated_citation_and_autonomy(bundle, analysis):
    bad = json.loads(json.dumps(analysis))
    bad["opportunities"][0]["evidence"].append({"source_id": "SUP-9999", "why": "made up"})
    bad["opportunities"][0]["task_keys"].append("SUP:not_a_task")
    s = next(o for o in bad["opportunities"] if "Sanctions" in o["title"])
    s["proposed_solution"] = "Auto-close sanctions alerts without analyst review."
    s["risk"] = 2
    v = validate(bad, bundle)
    first = v["per_opportunity"][bad["opportunities"][0]["id"]]
    assert any("SUP-9999" in i for i in first)
    assert any("Unknown task_keys" in i for i in first)
    issues = v["per_opportunity"][s["id"]]
    assert any("autonomous" in i for i in issues)
    assert any("low risk" in i for i in issues)
    assert v["grounding_rate"] < 1.0


def test_roi_math_matches_formula():
    tasks = pd.DataFrame([{"task_key": "SUP:x", "observed_count": 10, "avg_minutes": 30,
                           "volume_basis": "sample"}])
    opp = [{"id": "OPP-01", "title": "t", "task_keys": ["SUP:x"], "suggested_automatable_share": 0.5,
            "suggested_review_overhead": 0.2, "complexity": "S", "feasibility": 5, "risk": 1}]
    a = Assumptions(loaded_hourly_cost=50, sample_multipliers={"SUP": 20})
    r = compute(opp, tasks, a).iloc[0]
    # 10 × 20 = 200 items; 200 × 30 / 60 = 100 h; × 0.5 × 0.8 = 40 h; × $50 = $2,000/mo
    assert r.monthly_volume == 200
    assert r.baseline_hours_m == 100
    assert r.net_hours_saved_m == 40
    assert r.monthly_value_usd == 2000
    assert r.annual_net_value_usd == (2000 - 150) * 12
    assert r.build_cost_usd == 2 * a.weekly_build_cost
    assert r.phase.startswith("1")


def test_overrides_flow_through_and_risk_gate(bundle, analysis):
    base = compute(analysis["opportunities"], bundle.tasks, Assumptions())
    oid = base.iloc[0]["id"]
    edited = compute(analysis["opportunities"], bundle.tasks, Assumptions(),
                     {oid: {"automatable_share": 0.0}})
    assert edited.set_index("id").at[oid, "net_hours_saved_m"] == 0
    gated = compute(analysis["opportunities"], bundle.tasks, Assumptions(), {oid: {"risk": 5}})
    assert gated.set_index("id").at[oid, "phase"].startswith("3")


def test_llm_never_supplies_volumes(analysis):
    banned = {"monthly_volume", "hours", "hours_saved", "cost", "savings", "avg_minutes"}
    for o in analysis["opportunities"]:
        assert not banned & set(o), f"{o['id']} contains model-supplied numbers"
