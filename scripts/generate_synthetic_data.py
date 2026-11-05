"""Generate the synthetic dataset for Kestrel Pay, a FICTIONAL cross-border payments company.

Everything produced here is invented for demonstration. Volumes, handle times and
pain points are modeled on patterns common in African fintech operations, not on
any real company's data.

Run:  python scripts/generate_synthetic_data.py
Output: data/support_cases.csv, data/merchant_onboarding.csv, data/compliance_reviews.csv
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
DATA = Path(__file__).resolve().parent.parent / "data"
START = datetime(2026, 9, 1)  # 30-day observation window: Sep 1 – Sep 30, 2026

COUNTRIES = ["Nigeria", "Kenya", "Ghana", "South Africa", "United States", "United Kingdom"]
COUNTRY_W = [0.38, 0.2, 0.14, 0.1, 0.1, 0.08]
TIERS = ["Starter", "Growth", "Enterprise"]
TIER_W = [0.55, 0.33, 0.12]
CHANNELS = ["email", "in-app chat", "WhatsApp", "account manager"]

# category: (share, mean handle min, sd, escalation rate, touches range, subcategories, description templates)
SUPPORT = {
    "Payout status inquiry": (
        0.30, 9, 3, 0.03, (1, 2),
        ["Payout not received", "Payout delayed", "Payout reference request"],
        [
            "Merchant asking where payout {ref} is. Agent checked settlement dashboard, payout batched for next cycle. Copied ETA into reply.",
            "Merchant says {amt} USD payout to {bank} not received. Status in dashboard shows 'processing'. Shared standard settlement timeline.",
            "Follow-up on payout {ref}, merchant needs proof of payment for supplier. Pulled transfer reference from partner bank portal and pasted into email.",
            "Customer asking why weekend payout has not landed. Explained T+1 business-day cutoff (same macro reply as usual).",
        ],
    ),
    "Failed transaction / refund": (
        0.18, 18, 6, 0.12, (1, 3),
        ["Card declined", "Mobile money reversal", "Refund request"],
        [
            "End customer debited but merchant shows failed txn {ref}. Checked processor logs, reversal auto-initiated, told merchant 3-5 days.",
            "Merchant wants to refund order {ref} ({amt} {cur}). Refund API returned error; agent processed manually in admin console.",
            "M-Pesa payment {ref} stuck pending. Queried partner status manually, confirmed reversal, updated merchant.",
        ],
    ),
    "KYC document resubmission": (
        0.14, 22, 7, 0.08, (2, 4),
        ["Expired ID", "Blurry document", "Proof of address mismatch"],
        [
            "Merchant onboarding blocked: director ID image unreadable. Requested re-upload, explained acceptable formats for third time.",
            "Utility bill address does not match registration certificate. Agent compared both PDFs by eye and requested a bank statement instead.",
            "Merchant uploaded CAC document in wrong slot. Agent re-tagged file manually and notified compliance queue.",
        ],
    ),
    "Settlement reconciliation mismatch": (
        0.10, 41, 14, 0.35, (2, 5),
        ["Amount mismatch", "Missing transactions", "FX difference"],
        [
            "Merchant settlement report short by {amt} {cur}. Agent exported internal ledger, partner bank statement and processor report, matched in Excel; 2 txns in next batch.",
            "Settlement file missing 14 transactions for {date}. Rebuilt list from ledger export; escalated to finance ops.",
            "Merchant disputes FX applied on USD settlement. Pulled rate snapshot from treasury sheet and recalculated manually.",
        ],
    ),
    "Chargeback / dispute": (
        0.08, 55, 18, 0.50, (3, 6),
        ["Card chargeback", "Fraud claim", "Evidence request"],
        [
            "Chargeback received on {ref} ({amt} USD). Agent gathered delivery evidence from merchant over 4 emails and compiled PDF for acquirer.",
            "Cardholder fraud claim. Collected IP/device logs and order details, wrote dispute narrative, submitted to scheme portal.",
        ],
    ),
    "API integration help": (
        0.08, 34, 12, 0.25, (2, 4),
        ["Webhook not firing", "Auth error", "Sandbox vs live confusion"],
        [
            "Developer reports webhooks not received. Agent checked delivery logs, endpoint returning 500. Pointed to docs section on retries.",
            "Merchant using live keys in sandbox, getting 401. Explained key types; same issue as many other tickets this month.",
            "Integration question about idempotency keys on payouts API. Escalated to solutions engineer.",
        ],
    ),
    "Account access / 2FA": (
        0.07, 12, 4, 0.05, (1, 2),
        ["2FA reset", "Locked account", "Add team member"],
        [
            "Merchant admin lost 2FA device. Agent verified identity via call-back and reset 2FA in admin console.",
            "Account locked after failed logins. Verified email ownership, unlocked.",
        ],
    ),
    "FX rate query": (
        0.05, 7, 2, 0.02, (1, 1),
        ["Rate quote", "Rate lock question"],
        [
            "Merchant asking today's NGN/USD settlement rate. Agent copied rate from treasury sheet.",
            "Question on how long a quoted rate is held. Sent standard explanation.",
        ],
    ),
}

BANKS = ["GTBank", "Equity Bank", "Access Bank", "Stanbic", "Ecobank", "Zenith"]
CUR = {"Nigeria": "NGN", "Kenya": "KES", "Ghana": "GHS", "South Africa": "ZAR",
       "United States": "USD", "United Kingdom": "GBP"}

ONBOARDING = [
    # step_id, name, owner, monthly_volume, avg_min, rework_rate, sla_hours, systems, sensitivity, notes
    ("ONB-01", "Application intake and completeness check", "Onboarding Associate", 420, 12, 0.28, 24,
     "Typeform; Google Sheets", "Low", "Associate checks 23 required fields by hand; ~28% of applications bounce back for missing items."),
    ("ONB-02", "Business registration document verification", "Onboarding Associate", 420, 18, 0.22, 48,
     "Registry portal; Google Drive", "Medium", "Registration number looked up manually on government registry portal and compared to uploaded certificate."),
    ("ONB-03", "Director / UBO identity verification", "Compliance Analyst", 420, 15, 0.15, 48,
     "ID vendor dashboard", "High", "Vendor returns match score; analyst reviews every result including high-confidence passes."),
    ("ONB-04", "Sanctions and PEP screening of directors/UBOs", "Compliance Analyst", 420, 8, 0.05, 24,
     "Screening tool", "High", "Screening is automated; analyst manually clears name-only partial matches."),
    ("ONB-05", "Website and business-model review (prohibited activities)", "Compliance Analyst", 380, 25, 0.10, 72,
     "Browser; internal policy PDF", "High", "Analyst browses merchant site, checks against prohibited/restricted list, writes summary."),
    ("ONB-06", "Risk scoring and tier assignment", "Compliance Analyst", 380, 10, 0.08, 24,
     "Risk matrix spreadsheet", "Medium", "Scores 9 factors in a spreadsheet; copies result into CRM."),
    ("ONB-07", "Settlement bank account verification", "Onboarding Associate", 360, 9, 0.18, 24,
     "Bank verification API; CRM", "Medium", "Name-on-account mismatches resolved by email back-and-forth."),
    ("ONB-08", "Pricing and contract generation", "Sales Ops", 340, 14, 0.12, 24,
     "Google Docs; DocuSign", "Low", "Contract assembled from template; pricing table retyped from CRM deal record."),
    ("ONB-09", "API key provisioning and sandbox setup email", "Onboarding Associate", 340, 6, 0.04, 8,
     "Admin console; Gmail", "Low", "Same welcome email sent each time with keys pasted in."),
    ("ONB-10", "Go-live checklist call", "Account Manager", 300, 30, 0.05, 72,
     "Zoom; checklist doc", "Low", "Walks merchant through a 15-item go-live checklist; most items are confirmable from logs."),
]

COMPLIANCE = {
    # type: (share, mean min, sd, outcome weights)
    "Sanctions screening alert (name match)": (0.40, 14, 5, {"Closed - false positive": 0.92, "Escalated to MLRO": 0.03, "Info requested": 0.05}),
    "Transaction monitoring alert": (0.30, 32, 10, {"Closed - false positive": 0.78, "Escalated to MLRO": 0.10, "Info requested": 0.12}),
    "Periodic KYC refresh": (0.18, 26, 8, {"Cleared": 0.80, "Info requested": 0.18, "Escalated to MLRO": 0.02}),
    "Enhanced due diligence (high-risk merchant)": (0.12, 95, 25, {"Cleared": 0.62, "Info requested": 0.25, "Escalated to MLRO": 0.13}),
}
CMP_NOTES = {
    "Sanctions screening alert (name match)": [
        "Partial name match on common surname; DOB and nationality differ from list entry. Cleared after manual comparison.",
        "Payee name fuzzy-matched a listed entity; different country and registration number. Cleared.",
        "Name match with differing middle name; pulled ID from onboarding file to confirm DOB.",
    ],
    "Transaction monitoring alert": [
        "Velocity rule fired on seasonal sales spike; merchant history consistent. Closed.",
        "Multiple payouts just under threshold. Reviewed 90 days of activity, documented rationale.",
        "Round-amount pattern flagged; matched invoices provided by merchant earlier.",
    ],
    "Periodic KYC refresh": [
        "Annual refresh: re-requested directors' IDs and checked registry for changes.",
        "Refresh: business address changed; requested new proof of address.",
    ],
    "Enhanced due diligence (high-risk merchant)": [
        "Crypto-adjacent merchant: reviewed licensing, source of funds, adverse media. Wrote 2-page memo.",
        "High-volume remittance merchant: reviewed ownership chain across 3 jurisdictions.",
    ],
}
ALERT_SRC = {
    "Sanctions screening alert (name match)": "Screening tool",
    "Transaction monitoring alert": "TM rules engine",
    "Periodic KYC refresh": "Refresh calendar",
    "Enhanced due diligence (high-risk merchant)": "Risk tier = High",
}


def _pick(weights: dict[str, float]) -> str:
    return random.choices(list(weights), weights=list(weights.values()))[0]


def gen_support(n: int = 200) -> list[dict]:
    cats = list(SUPPORT)
    shares = [SUPPORT[c][0] for c in cats]
    rows = []
    for i in range(1, n + 1):
        cat = random.choices(cats, weights=shares)[0]
        _, mu, sd, esc, touches, subs, templates = SUPPORT[cat]
        country = random.choices(COUNTRIES, weights=COUNTRY_W)[0]
        cur = CUR[country]
        created = START + timedelta(minutes=random.randint(0, 30 * 24 * 60 - 1))
        desc = random.choice(templates).format(
            ref=f"PO-{random.randint(100000, 999999)}", amt=f"{random.randint(80, 25000):,}",
            cur=cur, bank=random.choice(BANKS), date=(created - timedelta(days=1)).strftime("%b %d"),
        )
        escalated = random.random() < esc
        handle = max(2, round(random.gauss(mu, sd) + (12 if escalated else 0)))
        rows.append({
            "case_id": f"SUP-{i:04d}",
            "created_at": created.strftime("%Y-%m-%d %H:%M"),
            "channel": random.choice(CHANNELS),
            "category": cat,
            "subcategory": random.choice(subs),
            "merchant_tier": random.choices(TIERS, weights=TIER_W)[0],
            "country": country,
            "description": desc,
            "handle_time_min": handle,
            "touches": random.randint(*touches) + (1 if escalated else 0),
            "escalated": "yes" if escalated else "no",
        })
    # Realistic data-quality gaps: a few tickets without logged handle time
    for r in random.sample(rows, 4):
        r["handle_time_min"] = ""
    return rows


def gen_onboarding() -> list[dict]:
    keys = ["step_id", "step_name", "owner_role", "monthly_volume", "avg_minutes", "rework_rate",
            "sla_hours", "systems", "regulatory_sensitivity", "notes"]
    return [dict(zip(keys, row)) for row in ONBOARDING]


def gen_compliance(n: int = 150) -> list[dict]:
    types = list(COMPLIANCE)
    shares = [COMPLIANCE[t][0] for t in types]
    rows = []
    for i in range(1, n + 1):
        t = random.choices(types, weights=shares)[0]
        _, mu, sd, outcomes = COMPLIANCE[t]
        created = START + timedelta(minutes=random.randint(0, 30 * 24 * 60 - 1))
        rows.append({
            "review_id": f"CMP-{i:04d}",
            "created_at": created.strftime("%Y-%m-%d %H:%M"),
            "review_type": t,
            "alert_source": ALERT_SRC[t],
            "outcome": _pick(outcomes),
            "minutes_spent": max(4, round(random.gauss(mu, sd))),
            "analyst": random.choice(["Analyst A", "Analyst B", "Analyst C", "Analyst D"]),
            "notes": random.choice(CMP_NOTES[t]),
        })
    return rows


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows):>3} rows -> {path.relative_to(DATA.parent)}")


if __name__ == "__main__":
    random.seed(SEED)
    DATA.mkdir(exist_ok=True)
    write(DATA / "support_cases.csv", gen_support())
    write(DATA / "merchant_onboarding.csv", gen_onboarding())
    write(DATA / "compliance_reviews.csv", gen_compliance())
