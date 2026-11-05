# Loom walkthrough script (target 3–4 minutes)

**0:00 — Hook (15s)**
"Every ops leader I've worked with knows their team is buried in manual work. The hard part is knowing what to automate first, what it's worth, and what must stay human. I built an agent that answers those three questions with evidence."

**0:15 — The setup (20s)** *Show tab ①, toggle sample data, click Load.*
"This is Kestrel Pay, a fictional cross-border payments company. I modeled it on the operations I've seen at Lazerpay, Bitnob and WeWire: 200 support tickets, a 10-step merchant onboarding process, 150 compliance reviews, and interviews with three ops leads."
*Point at the task profile.* "These volumes and handle times are computed by code. The AI never makes up a number."

**0:35 — The AI analysis (60s)** *Tab ②, run analysis.*
"Claude reads the profile and the interviews and returns nine opportunities. Each one has the problem, the solution, what stays human, feasibility and risk scores."
*Open OPP-01, click a citation popover.* "Every claim cites a source. Here's the actual ticket, and here's the support lead saying the 2024 chatbot failed because it couldn't see payout data. That's why this design is grounded in merchant records."
*Point to metrics.* "Code checks every citation exists: 35 of 35. If the model invents a source, it shows up here in red."
*Scroll to Not recommended.* "Just as important: what not to automate. 2FA resets are an account-takeover risk. Refund failures are a bug to fix first."

**1:35 — Human approval (40s)** *Tab ③.*
"Nothing reaches the roadmap without a person. I'll approve everything at risk three or below. Sanctions stays at 'needs more info'."
*Edit one automatable_share, e.g. OPP-05 from 0.60 to 0.40.* "If I think the AI is optimistic, I change the assumption and the savings recalculate."

**2:15 — ROI and roadmap (50s)** *Tab ④.*
"About 740 net hours a month, roughly 4.7 FTE of capacity, after subtracting human review time."
*Point at the chart.* "Sanctions case prep has big hours, but the risk gate pushes it to Phase 3 until the MLRO agrees controls. Value doesn't override compliance."
*Download the roadmap.* "The output is a roadmap leadership can read without the app, with evidence, assumptions and a pilot metric for each item."

**3:05 — Honesty and close (25s)**
"To be clear: this is synthetic data and these are estimates. The demo proves the method and the build, not the impact. The next step is a pilot with real tickets, measuring handle time before and after. Code, sample data and evals are on GitHub."
