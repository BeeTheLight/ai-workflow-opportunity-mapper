"""Replace the illustrative demo analysis with a real Claude run on the sample data.

    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/refresh_demo_cache.py

Run this before you publish, so reviewers see genuine model output in demo mode.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mapper.ingest import load_sources  # noqa: E402
from mapper.llm import analyze  # noqa: E402
from mapper.validate import validate  # noqa: E402

CONTEXT = ("Kestrel Pay (fictional) is a cross-border payments company serving merchants in "
           "Nigeria, Kenya, Ghana, South Africa, the US and UK. Regulated by its sponsor bank; "
           "has an MLRO. ~45 operations staff across support, onboarding and compliance.")

if __name__ == "__main__":
    files = [(p.name, p.read_bytes()) for p in sorted((ROOT / "data").iterdir()) if p.suffix in {".csv", ".md"}]
    bundle = load_sources(files)
    result = analyze(bundle, CONTEXT)
    report = validate(result, bundle)
    print(f"grounding rate: {report['grounding_rate']:.0%}, issues on {report['opportunities_with_issues']} opps")
    out = ROOT / "sample_output" / "demo_analysis.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {out}")
