# AI automation roadmap — Kestrel Pay (fictional)
_Generated November 05, 2026 by AI Workflow Opportunity Mapper. Analysis source: illustrative, model: n/a (authored sample; replace with a live run)._

> All savings are **estimates** computed from the uploaded data and the assumptions listed below. They are not observed results. Impact should be measured in a pilot against a baseline before any figure is reported as achieved.

## Summary
Kestrel Pay's manual load is concentrated in three places: repetitive payout-status questions, onboarding intake rework, and false-positive compliance alerts. The fastest, lowest-risk wins are grounded self-service for payout status and a completeness pre-check on applications. The largest pool of hours sits in sanctions and monitoring alerts, but those are regulated decisions, so the recommendation is AI-prepared case files with analyst sign-off, phased in after controls are agreed with the MLRO.

**Approved opportunities:** 8 of 9  
**Estimated net hours saved / month:** 744 (≈ 4.7 FTE)  
**Estimated annual net value:** $214,160  
**Estimated one-time build cost:** $144,000

## Phase 1 · Quick wins (0–30 days)

### OPP-01 · Grounded payout-status answers in chat and agent assist
*Customer support · Retrieval-grounded self-service · feasibility 5/5 · risk 2/5 · complexity S*

**Problem.** About 30% of tickets ask where a payout is. The answer already exists in the settlement dashboard; agents look it up and paste it into a macro.

**Proposed solution.** Answer payout and FX-rate questions from the merchant's own settlement records via in-app chat and WhatsApp, citing the payout reference and expected date. Unresolved or unusual cases hand off to an agent with the lookup already done.

**What stays human.** Agents handle anything the record cannot explain (missing payouts, partner delays) and own customer-facing exceptions.

**Estimate.** 1,400 items/month · 123 net hours/month · $39,582/yr net · build $9,000 · payback 2.7 months

**Evidence.** `SUP-0002` Agent copies ETA from dashboard into reply; `SUP-0005` Same lookup-and-paste pattern; `NOTES-P02` Support lead: a third of the queue, answer is in the dashboard; `NOTES-P03` Past chatbot failed because it could not see payout status

**Open questions.**
- Does the settlement system expose a per-merchant API we can query in real time?

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-03 · Onboarding emails and go-live checklist from API logs
*Merchant onboarding · Deterministic rules / RPA · feasibility 5/5 · risk 1/5 · complexity S*

**Problem.** The sandbox welcome email is identical every time, and most of the 15-item go-live checklist can be confirmed from the merchant's own API activity.

**Proposed solution.** Trigger the welcome email automatically when keys are issued, and pre-fill the go-live checklist from API logs so the call covers only the items that are not yet green.

**What stays human.** Account managers keep the call for strategic merchants and anything red on the checklist.

**Estimate.** 640 items/month · 83 net hours/month · $26,021/yr net · build $9,000 · payback 4.2 months

**Evidence.** `ONB-09` Same welcome email sent each time; `ONB-10` 30-minute call walking a 15-item checklist; `NOTES-P09` Checklist items are confirmable from API logs; `SOP-P07` SOP: provision keys, send WEL-02, schedule go-live call

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-02 · Application completeness pre-check at submission
*Merchant onboarding · Document extraction and verification · feasibility 4/5 · risk 2/5 · complexity S*

**Problem.** Associates read every application against 23 fields and 4 documents; about 28% bounce back, which also generates document-resubmission tickets.

**Proposed solution.** Check fields and classify uploaded documents at the moment of submission (right document in the right slot, legible, not expired) and tell the merchant immediately what is missing.

**What stays human.** Associates review only flagged applications. Compliance judgments are unchanged.

**Estimate.** 860 items/month · 110 net hours/month · $35,337/yr net · build $9,000 · payback 3.1 months

**Evidence.** `ONB-01` 12 min per application, 28% rework rate; `SUP-0010` Agent requests re-upload of unreadable ID; `NOTES-P07` Onboarding manager: biggest drag is the first step; `SOP-P02` SOP defines 23 fields and 4 documents to check

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-04 · Developer-support answers grounded in API docs and request logs
*Customer support · Retrieval-grounded self-service · feasibility 4/5 · risk 1/5 · complexity S*

**Problem.** API tickets repeat (live keys in sandbox, failing webhooks) and the docs already answer most of them.

**Proposed solution.** Classify incoming developer tickets, check the merchant's recent API errors, and draft a reply that links the exact docs section. Simple cases are answered directly.

**What stays human.** Solutions engineers handle anything involving idempotency, money movement or custom builds.

**Estimate.** 340 items/month · 70 net hours/month · $21,829/yr net · build $9,000 · payback 4.9 months

**Evidence.** `SUP-0013` Live-key-in-sandbox ticket, 'same issue as many others'; `SUP-0004` Webhook endpoint returning 500; `NOTES-P06` Docs answer most API tickets, developers miss the page

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

## Phase 2 · Next (30–90 days)

### OPP-05 · Settlement reconciliation auto-matching with explanations
*Customer support · Deterministic rules / RPA · feasibility 3/5 · risk 3/5 · complexity M*

**Problem.** Each mismatch ticket means exporting three reports and matching in Excel; about a third still escalate to finance ops.

**Proposed solution.** Match ledger, partner-bank and processor records automatically, and have the model explain the remaining breaks in plain language (timing, FX, missing batch) for the agent to send.

**What stays human.** Finance ops resolves true breaks and signs off any balance adjustment.

**Estimate.** 380 items/month · 136 net hours/month · $38,663/yr net · build $27,000 · payback 8.4 months

**Evidence.** `SUP-0001` Agent exports three reports and matches in Excel; `SUP-0006` Missing transactions rebuilt from ledger export; `NOTES-P04` Support lead: most-dreaded ticket, up to an hour each

**Open questions.**
- Are partner-bank statements available by API or only as portal downloads?

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-07 · Transaction-monitoring and KYC-refresh rationale drafting
*Compliance operations · LLM drafting with human review · feasibility 4/5 · risk 3/5 · complexity M*

**Problem.** Most monitoring alerts are known seasonal patterns; the real cost is writing an audit-ready rationale for each one.

**Proposed solution.** Pull 90 days of merchant history, prior alerts and invoices into a case summary and draft the closing rationale for the analyst to edit and sign.

**What stays human.** The analyst decides every alert outcome and signs the rationale. Escalations to the MLRO are unchanged.

**Estimate.** 750 items/month · 91 net hours/month · $23,374/yr net · build $27,000 · payback 13.9 months

**Evidence.** `CMP-0003` Rationale written for a closed alert; `CMP-0008` 90 days of activity reviewed manually; `NOTES-P12` Real cost is writing rationale that survives audit; `NOTES-P13` AI may prepare the case file, not close alerts

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-06 · Registry lookup and bank-account name matching
*Merchant onboarding · Document extraction and verification · feasibility 3/5 · risk 3/5 · complexity M*

**Problem.** Associates type registration numbers into the government portal and compare results to certificates by eye; name-on-account mismatches cause email back-and-forth.

**Proposed solution.** Extract fields from the certificate, query the registry, and show a side-by-side match report with discrepancies highlighted. Fuzzy-match bank account names and draft the clarification email when needed.

**What stays human.** Associate confirms the match report; discrepancies go to a compliance analyst as today.

**Estimate.** 780 items/month · 68 net hours/month · $15,480/yr net · build $27,000 · payback 20.9 months

**Evidence.** `ONB-02` 18 min per application, 22% rework; `ONB-07` Name-on-account mismatches resolved by email; `NOTES-P08` Mechanical, but a wrong match creates exposure; `SOP-P03` SOP requires registry confirmation

**Open questions.**
- Does the registry offer an API or bulk lookup, or only a web portal?

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

### OPP-09 · Chargeback evidence pack assembly
*Customer support · Agentic case preparation · feasibility 3/5 · risk 3/5 · complexity M*

**Problem.** Agents chase merchants for evidence over several emails and write each dispute narrative by hand under strict scheme deadlines.

**Proposed solution.** Send the merchant a structured evidence request on day one, collect uploads in one place, and draft the dispute narrative from order, delivery and device data.

**What stays human.** Agents review and submit every dispute to the scheme portal.

**Estimate.** 300 items/month · 63 net hours/month · $13,874/yr net · build $27,000 · payback 23.4 months

**Evidence.** `SUP-0003` Evidence gathered over four emails; `SUP-0026` Narrative written manually from logs; `NOTES-P05` Strict scheme deadlines

**Pilot success metric.** Measure handle time and error/rework rate for 4 weeks before and after launch on the same task mix.

## Not approved / on hold

- **OPP-08 · Sanctions name-match case preparation** — Needs more info: Hold until MLRO agrees QA sampling rate and vendor DPA is signed.

## Deliberately not recommended for automation

- `CMP:enhanced_due_diligence_high_risk_merchant` — Low volume and judgment-heavy. Revisit adverse-media gathering only after the sanctions case-prep controls are proven.
- `ONB:website_and_business_model_review_prohibited_activities` — Determines eligibility under the prohibited-activities policy; keep human. A site summary could be added later as an input, not a decision.
- `ONB:risk_scoring_and_tier_assignment` — Sets the approval route. Moving the spreadsheet into the CRM is a systems fix, not AI.
- `SUP:account_access_2fa` — Identity reset is an account-takeover vector; automating it raises fraud risk.
- `SUP:failed_transaction_refund` — Root cause is a refund API error forcing manual processing. Fix the bug first.
- `ONB:director_ubo_identity_verification` — The vendor already automates this. Revisit the policy of reviewing every high-confidence pass before adding AI.
- `ONB:pricing_and_contract_generation` — Template merge from CRM; a standard integration, not an AI problem.

## Assumptions used

| Assumption | Value |
|---|---|
| Loaded cost per hour (USD) | 28.0 |
| Support sample multiplier | 20 |
| Compliance sample multiplier | 10 |
| Build cost per week (USD) | 4500.0 |
| Build weeks S/M/L | 2/6/12 |
| Risk gate | 4 |

## Method

1. Task volumes and handle times computed directly from uploaded data.
2. Claude identified opportunities, scored feasibility and risk, and cited source records.
3. Citations and task links were machine-checked against the sources.
4. Savings were calculated by deterministic code from the assumptions above.
5. A human reviewer approved, edited or rejected each opportunity.