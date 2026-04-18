# D8X Vision

## Problem

Enterprise SDLC is broken. A typical software project at a
Fortune 500 company involves:

- A BRD written in Word
- Requirements in Jira
- Architecture decisions in Confluence
- Meeting notes in OneNote
- Existing code in GitHub
- Schema in a SQL Server dump

Nobody can see across all of these. When a business rule in the
BRD contradicts a threshold in the code, nobody notices until
QA finds it in production. When an architect makes a decision
that violates a compliance requirement buried in page 47 of the
BRD, nobody notices until the audit fails.

Consulting firms spend 40+ hours per architect per week manually
reconciling these sources. A typical modernization project has
a 3-month "analysis phase" that is almost entirely manual reading,
highlighting, and Excel-tracking.

## Solution

D8X ingests heterogeneous inputs (any format), extracts business
rules and entities, detects conflicts across sources, and produces
architecture, planning, and code — with a human approval gate
at every stage.

The patent claim: **cross-source conflict detection.** No other
tool does this. D8X finds that the BRD says $10,000 approval
threshold but the Python code uses $5,000. It finds that the
meeting notes say 10-year retention but the BRD says 7 years.
It finds that the schema stores SSN plaintext while the
compliance document requires encryption at rest.

## Target Customer (first 12 months)

**Primary:** Mid-market consulting firms (10-200 people)
doing SDLC work for enterprise clients. Examples:
Slalom, EPAM, Thoughtworks, regional consultancies.

**Secondary (later):** Enterprise architecture teams at
Fortune 1000 companies doing internal modernization.

## Pricing

- **Pilot (first 5 customers):** $500/month, 3-month commitment
- **Team:** $2,000/month, unlimited projects
- **Enterprise:** $50K+/year, dedicated tenant, custom adapters, SLA

## Success Metrics

### 3 months
- 10 consulting firms in pilot ($5K MRR)
- D2: Discover quality score > 85 on test corpus
- Jira + Confluence integrations live

### 6 months
- 5 paid customers ($10K MRR)
- Full 8-agent pipeline working end-to-end
- SOC 2 Type 1 in progress

### 12 months
- 20 paid customers ($50K MRR = $600K ARR)
- Mid-market SaaS expansion begins
- SOC 2 Type 2 complete
- Hire first employee (engineer or sales)