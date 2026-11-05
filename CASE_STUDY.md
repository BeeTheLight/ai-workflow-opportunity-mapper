# Case study: AI Workflow Opportunity Mapper

**Barakat "Bee" Olatinwo** · AI strategy portfolio project · November 2026

## The problem

Operations leaders know their teams are buried in manual work but struggle to answer three questions with evidence: *which* work to automate, *how much* it is worth, and *what must stay human*. In payments, the last question carries regulatory weight. Generic "AI opportunity" workshops produce slideware; generic chatbots produce confident numbers with no audit trail.

Having worked in operations-heavy fintechs across African markets (Lazerpay, Bitnob, WeWire), I wanted a tool that does what a good ops strategist does: read the data and the interviews, separate repetitive work from judgment work, and hand leadership a plan they can check.

## What I built

A working app that takes process CSVs and interview notes, and returns a ranked, cited, human-approved automation roadmap.

1. **Profile (code).** Volumes, handle times and escalation rates are computed from the data.
2. **Analyze (Claude).** The model identifies opportunities, explains them, scores feasibility and risk, names what stays human, lists what *not* to automate, and cites source records and interview paragraphs by ID.
3. **Verify (code).** Every citation and task link is checked against the uploads; regulated steps proposed at low risk or with autonomous decisions are flagged.
4. **Estimate (code).** Savings, payback, priority and phase come from transparent formulas and editable assumptions.
5. **Approve (human).** A reviewer approves, rejects or edits each recommendation; changes flow into the numbers and an audit trail.

## Key design tradeoffs

| Decision | Why | Cost |
|---|---|---|
| LLM never produces numbers | Hallucinated savings destroy trust; formulas are auditable | Model can't "notice" volume patterns outside the profile |
| Forced structured output with citations | Every claim traceable to a record or quote | Less free-form insight |
| Risk gate overrides value | A sanctions automation can top the value chart and still be sequenced last | Some value deferred |
| "Not recommended" is a required output | Knowing what not to automate is half the job in regulated ops | Longer outputs |
| Demo mode with saved analysis | Reviewers can try it free, instantly | Must be refreshed with a live run before publishing |

## Demonstrated results (on synthetic data)

Kestrel Pay, a fictional cross-border payments company: 200 support tickets, a 10-step onboarding process, 150 compliance reviews, and three ops-lead interviews.

- **9 opportunities** identified across support, onboarding and compliance; **7 tasks deliberately excluded** (e.g. 2FA resets as an account-takeover vector; refund failures as a bug to fix, not automate).
- **Phase 1 quick wins:** grounded payout-status answers, application completeness pre-check, automated onboarding emails and go-live checklist, docs-grounded developer support.
- **Sanctions name-match case preparation** ranked high on hours but was gated to Phase 3 pending MLRO-agreed controls, matching the compliance lead's stated boundary.
- With 8 of 9 approved: **≈ 744 net hours/month (≈ 4.7 FTE of capacity)**, **≈ $214K estimated annual net value**, **≈ $144K estimated build cost**, under default assumptions.

_Update after your live run: grounding rate, recall vs. expert labels, false positives, run-to-run stability._

## Estimated vs. observed

Every figure above is an **estimate** from synthetic data and editable assumptions. It shows the method works and the build is sound. It does not show adoption or realized savings. The roadmap therefore attaches a pilot metric to each item: measure handle time and rework on the same task mix for four weeks before and after launch, and report only the observed difference.

## What I would do next

- Pilot on real (anonymized) ticket exports with an ops team and compare the agent's picks to the team's own.
- Add a second pass where the model proposes the specific pilot design and baseline for each approved item.
- Replace complexity tiers with build estimates from engineering.

**Stack:** Python · Streamlit · Claude API (tool-forced structured output) · pandas · Plotly · pytest
