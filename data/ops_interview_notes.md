# Kestrel Pay — Operations discovery interviews (FICTIONAL)

Interviews conducted Sep 2026 with three operations leads. Kestrel Pay is an invented company used for demonstration only.

## Support lead

Roughly a third of our queue is "where is my payout". The answer is almost always already in the settlement dashboard — agents look it up and paste the ETA into a macro. It is the most boring work we do and it is what merchants wait longest for at month end.

We tried a generic chatbot in 2024 and merchants hated it because it could not see their actual payout status. It just linked to the FAQ. Anything we build has to be grounded in the merchant's own transaction data or it will fail again.

Settlement mismatches are the tickets my team dreads. An agent exports the internal ledger, the partner bank statement and the processor report, then matches them in Excel. One ticket can take most of an hour, and a third of them still get escalated to finance ops.

Chargebacks are slow because we chase the merchant for evidence over several emails and then write the dispute narrative by hand. The scheme deadlines are strict, so we cannot let these sit.

API tickets repeat. Live keys used in sandbox, webhook endpoints returning errors. The docs answer most of them, but developers do not find the right page.

## Onboarding manager

Our biggest drag is the first step. Close to 30% of applications come back because of a missing field or the wrong document in the wrong slot, and an associate has to read every application line by line to catch it.

Registration documents are verified by typing the registration number into the government registry portal and comparing the result with the uploaded certificate by eye. It is mechanical, but a wrong match here creates real exposure.

The welcome and sandbox email is the same every time. Associates paste keys into a template. The go-live call is mostly ticking a checklist we could confirm from the merchant's API logs.

We would happily let software draft and pre-check things, but a human has to own the final approve or decline on any merchant. Our sponsor bank expects that.

## Compliance lead

More than nine in ten sanctions name-match alerts are false positives — common surnames, different date of birth, different country. Analysts spend their day re-checking fields the system already has.

Transaction monitoring alerts are mostly seasonal spikes we have seen before. The real cost is writing up the rationale for closing each one so it survives an audit.

Anything that decides whether to file a suspicious activity report, or that clears a high-risk merchant, must stay with a named analyst and the MLRO. I would accept AI that prepares the case file and summarizes the evidence. I would not accept AI that closes alerts on its own.

Customer personal data cannot be sent to tools that store it outside our approved processors. Any AI vendor needs a data processing agreement and no training on our data.

Enhanced due diligence memos take an analyst most of a morning. Half of that is gathering adverse-media results and licensing information into one place before any judgment happens.
