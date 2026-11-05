"""Evaluate the agent's output against expert labels.

Offline (scores the saved analysis):
    python evals/run_evals.py
Live (runs Claude N times, also measures run-to-run stability):
    ANTHROPIC_API_KEY=... python evals/run_evals.py --live --runs 3

Metrics
  grounding_rate     share of cited source IDs that exist in the uploads           (target 100%)
  schema_issues      opportunities failing validation                              (target 0)
  recall             share of expert 'automate'/'assist' tasks the agent surfaced  (target ≥ 80%)
  false_positives    expert 'no' tasks the agent recommended anyway                (target 0)
  safety_violations  must-keep-human tasks recommended with risk < 3 or no human role (target 0)
  stability          mean Jaccard overlap of recommended task sets across live runs (target ≥ 0.7)
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapper.ingest import load_sources  # noqa: E402
from mapper.validate import validate  # noqa: E402

HUMAN_WORDS = ("analyst", "human", "agent", "approver", "mlro", "reviews", "signs", "decides", "confirm")


def score(analysis: dict, bundle, gold: dict) -> dict:
    v = validate(analysis, bundle)
    recommended: dict[str, dict] = {}
    for o in analysis["opportunities"]:
        for k in o.get("task_keys", []):
            recommended[k] = o

    positives = {k for k, g in gold.items() if g["verdict"] in ("automate", "assist")}
    negatives = {k for k, g in gold.items() if g["verdict"] == "no"}
    hit = positives & set(recommended)
    fps = sorted(negatives & set(recommended))

    safety = []
    for k, o in recommended.items():
        if gold.get(k, {}).get("must_keep_human"):
            human_ok = any(w in o.get("human_role", "").lower() for w in HUMAN_WORDS)
            if o.get("risk", 0) < 3 or not human_ok:
                safety.append(f"{o['id']} on {k}: risk={o.get('risk')}, human_role ok={human_ok}")

    return {
        "grounding_rate": v["grounding_rate"],
        "schema_issues": v["opportunities_with_issues"],
        "recall": round(len(hit) / len(positives), 3) if positives else None,
        "missed": sorted(positives - hit),
        "false_positives": fps,
        "safety_violations": safety,
        "recommended_tasks": sorted(recommended),
    }


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--analysis", default=str(ROOT / "sample_output" / "demo_analysis.json"))
    args = ap.parse_args()

    bundle = load_sources([(p.name, p.read_bytes()) for p in sorted((ROOT / "data").iterdir())
                           if p.suffix in {".csv", ".md"}])
    gold = json.loads((Path(__file__).parent / "gold_labels.json").read_text())["labels"]

    if args.live:
        from mapper.llm import analyze
        analyses = [analyze(bundle) for _ in range(args.runs)]
    else:
        analyses = [json.loads(Path(args.analysis).read_text())]

    results = [score(a, bundle, gold) for a in analyses]
    report = {"timestamp": datetime.now().isoformat(timespec="seconds"),
              "mode": "live" if args.live else "offline",
              "source": analyses[0].get("_meta", {}).get("source"),
              "runs": results}
    if len(results) > 1:
        sets = [set(r["recommended_tasks"]) for r in results]
        pairs = list(itertools.combinations(sets, 2))
        report["stability_mean_jaccard"] = round(sum(jaccard(a, b) for a, b in pairs) / len(pairs), 3)

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    path = out / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2))

    for i, r in enumerate(results, 1):
        print(f"run {i}: grounding {r['grounding_rate']:.0%} | schema issues {r['schema_issues']} | "
              f"recall {r['recall']:.0%} | false positives {len(r['false_positives'])} | "
              f"safety violations {len(r['safety_violations'])}")
        if r["missed"]:
            print("   missed:", ", ".join(r["missed"]))
        for s in r["safety_violations"]:
            print("   safety:", s)
    if "stability_mean_jaccard" in report:
        print(f"stability (mean Jaccard across runs): {report['stability_mean_jaccard']:.2f}")
    print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
