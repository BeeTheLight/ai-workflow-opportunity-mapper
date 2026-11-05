# 🧭 AI Workflow Opportunity Mapper

An AI agent that reads an organization's process data and interview notes, finds the manual work worth automating, explains why with cited evidence, estimates the savings, and produces a phased roadmap a human approves.

**Live demo:** _add your Streamlit Cloud URL_ · **Walkthrough:** _add your Loom link_ · **Case study:** [CASE_STUDY.md](CASE_STUDY.md)

> All data is synthetic and every savings figure is an **estimate**. The demo shows the design and build; it does not show adoption or observed impact.

## The core design decision

| | Who does it | Where |
|---|---|---|
| Count volumes, average handle times, escalation rates | **Code** | `mapper/ingest.py` |
| Find opportunities, reason about them, score feasibility and risk, cite sources | **Claude** | `mapper/llm.py` |
| Verify every citation exists, every task is real, regulated steps keep a human | **Code** | `mapper/validate.py` |
| Calculate hours, value, payback, priority and phase | **Code** | `mapper/roi.py` |
| Approve, reject, edit assumptions | **Human** | Review tab in `app.py` |

The model never produces a volume, an hour count or a dollar figure. It suggests two assumptions per opportunity (share of time automatable, share of saved time spent on human review). Those are shown as suggestions, are editable, and feed transparent formulas:

```
net_hours / month = monthly_volume × avg_minutes ÷ 60 × automatable_share × (1 − review_overhead)
annual_net_value  = (net_hours × loaded_hourly_cost − monthly_run_cost) × 12
payback_months    = build_weeks[complexity] × weekly_build_cost ÷ monthly net value
priority (0–100)  = weighted(value, feasibility, inverse risk)
phase             = 1 if feasibility ≥ 4, risk ≤ 2, small build · 3 if risk ≥ gate or large build · else 2
```

## The demo scenario

**Kestrel Pay** is a fictional cross-border payments company (merchants in Nigeria, Kenya, Ghana, South Africa, the US and UK). The sample inputs in `data/`:

| File | What it is |
|---|---|
| `support_cases.csv` | 200 support tickets from a 30-day window (8 categories, handle times, escalations) |
| `merchant_onboarding.csv` | 10-step onboarding process map with monthly volumes, minutes and rework rates |
| `compliance_reviews.csv` | 150 sanctions, transaction-monitoring, KYC-refresh and EDD reviews |
| `ops_interview_notes.md` | Discovery interviews with the support, onboarding and compliance leads |
| `sop_merchant_onboarding.md` | The onboarding SOP |

Regenerate the CSVs with `python scripts/generate_synthetic_data.py` (seeded, reproducible).

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Demo mode works with no API key. For Live mode, paste a key in the sidebar or set `ANTHROPIC_API_KEY`.

## Before you publish: replace the illustrative analysis

`sample_output/demo_analysis.json` is what demo mode replays. The version in this repo was **written by hand to match the synthetic data** so the app works out of the box. Replace it with a genuine model run before you share the link:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/refresh_demo_cache.py      # writes a live analysis, prints its grounding rate
python evals/run_evals.py --live --runs 3 # scores it and measures run-to-run stability
```

The app labels which one it is showing.

## Evaluation approach

`evals/run_evals.py` scores the agent against expert labels in `evals/gold_labels.json` (22 tasks, each labeled *automate*, *assist* or *no*, plus whether a human must keep the decision).

| Metric | What it catches | Target |
|---|---|---|
| Grounding rate | Cited source IDs that do not exist | 100% |
| Schema issues | Bad task links, out-of-range scores | 0 |
| Recall | Good opportunities the agent missed | ≥ 80% |
| False positives | Tasks recommended that should not be automated | 0 |
| Safety violations | Regulated tasks recommended at low risk or with no human role | 0 |
| Stability | Jaccard overlap of recommended tasks across repeated runs | ≥ 0.7 |

Unit tests for ingest, validation and ROI math: `pytest -q`.

Note: scoring the hand-written demo analysis against labels from the same author is circular. The eval is meaningful on live runs.

## Deploy (Streamlit Community Cloud)

1. Push this folder to a public GitHub repo.
2. At share.streamlit.io → **New app** → pick the repo, branch, `app.py`.
3. Optional: in **Settings → Secrets**, add `ANTHROPIC_API_KEY` (see `.streamlit/secrets.toml.example`). If you do, visitors' Live runs bill to your key; the app caps hosted-key runs at 3 per session. Leaving it unset keeps the public demo free, and visitors can bring their own key.

## Use your own data

Upload any CSV with a task/category column and a minutes column (`task,minutes`, `category,handle_time_min`, ...). Add `monthly_volume` when rows are process steps rather than individual cases, and use the sidebar multiplier when rows are a sample. Upload interview notes or SOPs as `.md` or `.txt`; each paragraph becomes a citable source.

## Project structure

```
app.py                      Streamlit UI: inputs → AI analysis → review → ROI & roadmap
mapper/ingest.py            CSV/doc parsing, task profiling, source IDs
mapper/llm.py               Prompt, tool schema, Claude call
mapper/validate.py          Citation and safety checks
mapper/roi.py               Deterministic savings and prioritization
mapper/roadmap.py           Markdown roadmap export
data/                       Synthetic Kestrel Pay inputs
sample_output/              Demo analysis, example roadmap and ROI table
evals/                      Gold labels and eval runner
tests/                      Unit tests
scripts/                    Data generator, demo-cache builders
```

## Limits

- Synthetic data; real ops data is messier (free-text categories, missing timestamps, multi-touch tickets).
- Savings assume time freed is redeployed; they are capacity, not cash, unless headcount plans change.
- Build costs and run costs are rough tiers; replace them with real estimates for a business case.
- Sending customer data to an LLM requires a data processing agreement and an approved-processor review.
