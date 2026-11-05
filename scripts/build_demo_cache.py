"""Write sample_output/demo_analysis.json — the analysis shown in demo mode (no API key).

IMPORTANT: this file is an ILLUSTRATIVE analysis written to match the synthetic data, so the
public demo works without a key. Before publishing, replace it with a real model run:

    ANTHROPIC_API_KEY=sk-... python scripts/refresh_demo_cache.py

The app labels which one it is showing (meta.source = "illustrative" vs "live").
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "sample_output" / "demo_analysis.json"


def opp(i, title, process, keys, problem, solution, pattern, human, feas, feas_r, risk, risk_r,
        cx, share, overhead, evidence, questions=()):
    return {
        "id": f"OPP-{i:02d}", "title": title, "process": process, "task_keys": keys,
        "problem": problem, "proposed_solution": solution, "automation_pattern": pattern,
        "human_role": human, "feasibility": feas, "feasibility_rationale": feas_r,
        "risk": risk, "risk_rationale": risk_r, "complexity": cx,
        "suggested_automatable_share": share, "suggested_review_overhead": overhead,
        "evidence": [{"source_id": s, "why": w} for s, w in evidence],
        "open_questions": list(questions),
    }


analysis = {
    "summary": (
        "Kestrel Pay's manual load is concentrated in three places: repetitive payout-status "
        "questions, onboarding intake rework, and false-positive compliance alerts. The fastest, "
        "lowest-risk wins are grounded self-service for payout status and a completeness pre-check "
        "on applications. The largest pool of hours sits in sanctions and monitoring alerts, but "
        "those are regulated decisions, so the recommendation is AI-prepared case files with analyst "
        "sign-off, phased in after controls are agreed with the MLRO."
    ),
    "opportunities": [
        opp(1, "Grounded payout-status answers in chat and agent assist", "Customer support",
            ["SUP:payout_status_inquiry", "SUP:fx_rate_query"],
            "About 30% of tickets ask where a payout is. The answer already exists in the settlement "
            "dashboard; agents look it up and paste it into a macro.",
            "Answer payout and FX-rate questions from the merchant's own settlement records via in-app "
            "chat and WhatsApp, citing the payout reference and expected date. Unresolved or unusual "
            "cases hand off to an agent with the lookup already done.",
            "Retrieval-grounded self-service",
            "Agents handle anything the record cannot explain (missing payouts, partner delays) and "
            "own customer-facing exceptions.",
            5, "Data is structured and already in the settlement system; answer templates exist.",
            2, "Wrong ETA is an annoyance, not a regulatory issue. The 2024 chatbot failed because it "
               "was not grounded in merchant data, which this design addresses.",
            "S", 0.65, 0.10,
            [("SUP-0002", "Agent copies ETA from dashboard into reply"),
             ("SUP-0005", "Same lookup-and-paste pattern"),
             ("NOTES-P02", "Support lead: a third of the queue, answer is in the dashboard"),
             ("NOTES-P03", "Past chatbot failed because it could not see payout status")],
            ["Does the settlement system expose a per-merchant API we can query in real time?"]),
        opp(2, "Application completeness pre-check at submission", "Merchant onboarding",
            ["ONB:application_intake_and_completeness_check", "SUP:kyc_document_resubmission"],
            "Associates read every application against 23 fields and 4 documents; about 28% bounce "
            "back, which also generates document-resubmission tickets.",
            "Check fields and classify uploaded documents at the moment of submission (right document "
            "in the right slot, legible, not expired) and tell the merchant immediately what is missing.",
            "Document extraction and verification",
            "Associates review only flagged applications. Compliance judgments are unchanged.",
            4, "Field checks are rules; document classification and legibility checks are mature.",
            2, "Pre-check only gates completeness, not eligibility. Errors send a merchant back to "
               "upload again, which is the current outcome anyway.",
            "S", 0.55, 0.20,
            [("ONB-01", "12 min per application, 28% rework rate"),
             ("SUP-0010", "Agent requests re-upload of unreadable ID"),
             ("NOTES-P07", "Onboarding manager: biggest drag is the first step"),
             ("SOP-P02", "SOP defines 23 fields and 4 documents to check")]),
        opp(3, "Onboarding emails and go-live checklist from API logs", "Merchant onboarding",
            ["ONB:api_key_provisioning_and_sandbox_setup_email", "ONB:go_live_checklist_call"],
            "The sandbox welcome email is identical every time, and most of the 15-item go-live "
            "checklist can be confirmed from the merchant's own API activity.",
            "Trigger the welcome email automatically when keys are issued, and pre-fill the go-live "
            "checklist from API logs so the call covers only the items that are not yet green.",
            "Deterministic rules / RPA",
            "Account managers keep the call for strategic merchants and anything red on the checklist.",
            5, "Template and log data already exist.",
            1, "Low exposure: worst case is an unnecessary call.",
            "S", 0.50, 0.10,
            [("ONB-09", "Same welcome email sent each time"),
             ("ONB-10", "30-minute call walking a 15-item checklist"),
             ("NOTES-P09", "Checklist items are confirmable from API logs"),
             ("SOP-P07", "SOP: provision keys, send WEL-02, schedule go-live call")]),
        opp(4, "Developer-support answers grounded in API docs and request logs", "Customer support",
            ["SUP:api_integration_help"],
            "API tickets repeat (live keys in sandbox, failing webhooks) and the docs already answer "
            "most of them.",
            "Classify incoming developer tickets, check the merchant's recent API errors, and draft a "
            "reply that links the exact docs section. Simple cases are answered directly.",
            "Retrieval-grounded self-service",
            "Solutions engineers handle anything involving idempotency, money movement or custom builds.",
            4, "Docs and error logs are structured; error classes are few.",
            1, "Technical guidance only; no money movement.",
            "S", 0.40, 0.15,
            [("SUP-0013", "Live-key-in-sandbox ticket, 'same issue as many others'"),
             ("SUP-0004", "Webhook endpoint returning 500"),
             ("NOTES-P06", "Docs answer most API tickets, developers miss the page")]),
        opp(5, "Settlement reconciliation auto-matching with explanations", "Customer support",
            ["SUP:settlement_reconciliation_mismatch"],
            "Each mismatch ticket means exporting three reports and matching in Excel; about a third "
            "still escalate to finance ops.",
            "Match ledger, partner-bank and processor records automatically, and have the model explain "
            "the remaining breaks in plain language (timing, FX, missing batch) for the agent to send.",
            "Deterministic rules / RPA",
            "Finance ops resolves true breaks and signs off any balance adjustment.",
            3, "Matching logic is deterministic, but needs reliable report feeds from partners.",
            3, "A wrong explanation to a merchant about money is a trust issue; adjustments stay manual.",
            "M", 0.60, 0.20,
            [("SUP-0001", "Agent exports three reports and matches in Excel"),
             ("SUP-0006", "Missing transactions rebuilt from ledger export"),
             ("NOTES-P04", "Support lead: most-dreaded ticket, up to an hour each")],
            ["Are partner-bank statements available by API or only as portal downloads?"]),
        opp(6, "Registry lookup and bank-account name matching", "Merchant onboarding",
            ["ONB:business_registration_document_verification", "ONB:settlement_bank_account_verification"],
            "Associates type registration numbers into the government portal and compare results to "
            "certificates by eye; name-on-account mismatches cause email back-and-forth.",
            "Extract fields from the certificate, query the registry, and show a side-by-side match "
            "report with discrepancies highlighted. Fuzzy-match bank account names and draft the "
            "clarification email when needed.",
            "Document extraction and verification",
            "Associate confirms the match report; discrepancies go to a compliance analyst as today.",
            3, "Registry access method is uncertain; extraction itself is mature.",
            3, "A false match creates exposure, so every result is human-confirmed.",
            "M", 0.50, 0.25,
            [("ONB-02", "18 min per application, 22% rework"),
             ("ONB-07", "Name-on-account mismatches resolved by email"),
             ("NOTES-P08", "Mechanical, but a wrong match creates exposure"),
             ("SOP-P03", "SOP requires registry confirmation")],
            ["Does the registry offer an API or bulk lookup, or only a web portal?"]),
        opp(7, "Transaction-monitoring and KYC-refresh rationale drafting", "Compliance operations",
            ["CMP:transaction_monitoring_alert", "CMP:periodic_kyc_refresh"],
            "Most monitoring alerts are known seasonal patterns; the real cost is writing an "
            "audit-ready rationale for each one.",
            "Pull 90 days of merchant history, prior alerts and invoices into a case summary and draft "
            "the closing rationale for the analyst to edit and sign.",
            "LLM drafting with human review",
            "The analyst decides every alert outcome and signs the rationale. Escalations to the MLRO "
            "are unchanged.",
            4, "Inputs are structured; drafting from them is a strong LLM use case.",
            3, "Regulated record; mitigated by mandatory analyst sign-off and an audit trail of edits.",
            "M", 0.35, 0.30,
            [("CMP-0003", "Rationale written for a closed alert"),
             ("CMP-0008", "90 days of activity reviewed manually"),
             ("NOTES-P12", "Real cost is writing rationale that survives audit"),
             ("NOTES-P13", "AI may prepare the case file, not close alerts")]),
        opp(8, "Sanctions name-match case preparation", "Compliance operations",
            ["CMP:sanctions_screening_alert_name_match", "ONB:sanctions_and_pep_screening_of_directors_ubos"],
            "Over 90% of name-match alerts are false positives; analysts re-check DOB and country "
            "fields the system already holds.",
            "For each alert, assemble the list entry and the customer's verified identity data side "
            "by side, highlight differing fields, and pre-draft the disposition note. The analyst "
            "makes and records the decision.",
            "Agentic case preparation",
            "A named analyst clears or escalates every alert. No alert is closed by software.",
            4, "Field comparison is simple; the work is integration and controls.",
            4, "Sanctions decisions carry regulatory liability; requires MLRO-agreed controls, "
               "sampling QA and a data processing agreement for any AI vendor.",
            "M", 0.45, 0.35,
            [("CMP-0001", "Cleared after manual DOB and nationality comparison"),
             ("CMP-0002", "Fuzzy match on a different country and registration"),
             ("NOTES-P11", "More than nine in ten alerts are false positives"),
             ("NOTES-P13", "Must stay with a named analyst"),
             ("NOTES-P14", "Personal data only to approved processors"),
             ("SOP-P04", "Partial matches cleared by analyst with recorded rationale")],
            ["Will the MLRO accept AI-prepared case files, and what QA sampling rate?"]),
        opp(9, "Chargeback evidence pack assembly", "Customer support",
            ["SUP:chargeback_dispute"],
            "Agents chase merchants for evidence over several emails and write each dispute narrative "
            "by hand under strict scheme deadlines.",
            "Send the merchant a structured evidence request on day one, collect uploads in one place, "
            "and draft the dispute narrative from order, delivery and device data.",
            "Agentic case preparation",
            "Agents review and submit every dispute to the scheme portal.",
            3, "Evidence formats vary by merchant.",
            3, "Missed deadlines or weak narratives lose money; human submits.",
            "M", 0.35, 0.30,
            [("SUP-0003", "Evidence gathered over four emails"),
             ("SUP-0026", "Narrative written manually from logs"),
             ("NOTES-P05", "Strict scheme deadlines")]),
    ],
    "not_recommended": [
        {"task_key": "CMP:enhanced_due_diligence_high_risk_merchant",
         "reason": "Low volume and judgment-heavy. Revisit adverse-media gathering only after the "
                   "sanctions case-prep controls are proven."},
        {"task_key": "ONB:website_and_business_model_review_prohibited_activities",
         "reason": "Determines eligibility under the prohibited-activities policy; keep human. A site "
                   "summary could be added later as an input, not a decision."},
        {"task_key": "ONB:risk_scoring_and_tier_assignment",
         "reason": "Sets the approval route. Moving the spreadsheet into the CRM is a systems fix, not AI."},
        {"task_key": "SUP:account_access_2fa",
         "reason": "Identity reset is an account-takeover vector; automating it raises fraud risk."},
        {"task_key": "SUP:failed_transaction_refund",
         "reason": "Root cause is a refund API error forcing manual processing. Fix the bug first."},
        {"task_key": "ONB:director_ubo_identity_verification",
         "reason": "The vendor already automates this. Revisit the policy of reviewing every "
                   "high-confidence pass before adding AI."},
        {"task_key": "ONB:pricing_and_contract_generation",
         "reason": "Template merge from CRM; a standard integration, not an AI problem."},
    ],
    "_meta": {"source": "illustrative", "model": "n/a (authored sample; replace with a live run)"},
}

if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
